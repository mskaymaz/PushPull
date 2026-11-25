"""GitHub Releases upload helpers powered by GitHub CLI (`gh`)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.services.git_runner import CREATE_NO_WINDOW, run_git

PUBLIC_RELEASE_REPO = "mskaymaz/MSKLabsApps"
CF_DL_BASE = "https://msklabsdesk-backend.msklabs-org.workers.dev/dl"
CF_R2_BASE = "https://releases.msklabs.org"


def detect_repo_slug(repo_path: str | Path) -> str | None:
    """Extract `owner/repo` from the repository's `origin` remote URL."""
    res = run_git(repo_path, ["remote", "get-url", "origin"])
    if not res.ok:
        return None

    url = res.stdout.strip()
    https_match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if https_match:
        return https_match.group(1)
    return None


def to_app_slug(name: str) -> str:
    """Convert a repository name into a lowercase kebab-case slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return cleaned or "app"


def _norm_token(value: str) -> str:
    """Normalize a repo or file stem for matching (strip M_/D_/W_ prefixes)."""
    stripped = re.sub(r"^[a-zA-Z]_", "", value.strip())
    return re.sub(r"[^a-zA-Z0-9]+", "", stripped).lower()


def _pick_preferred_binary(
    candidates: list[Path],
    repo_name: str,
    fallback_stem: str | None = None,
) -> Path | None:
    """Pick the release binary matching repo_name or fallback_stem, excluding debug/profile."""
    valid = [
        p for p in candidates
        if p.is_file() and not any(bad in p.stem.lower() for bad in ("debug", "profile", "unins"))
    ]
    if not valid:
        return None

    target_tok = _norm_token(repo_name)
    for path in valid:
        if _norm_token(path.stem) == target_tok:
            return path

    if fallback_stem:
        for path in valid:
            if path.stem.lower() == fallback_stem:
                return path

    return max(valid, key=lambda p: p.stat().st_mtime)


def suggest_artifact(repo_path: str | Path) -> str:
    """Return the release binary (.exe or .apk) inside repo_path, excluding debug builds."""
    root = Path(repo_path)
    repo_name = root.name

    exe = _pick_preferred_binary(list((root / "dist").glob("*.exe")), repo_name)
    if exe is not None:
        return str(exe)

    apk = _pick_preferred_binary(
        list((root / "build" / "app" / "outputs" / "flutter-apk").glob("*.apk")),
        repo_name,
        fallback_stem="app-release",
    )
    return str(apk) if apk is not None else ""


def fetch_latest_public_version(app_slug: str) -> tuple[int, int, int] | None:
    """Return the highest (major, minor, patch) tag on MSKLabsApps for app_slug."""
    cmd = [
        "gh",
        "release",
        "list",
        "-R",
        PUBLIC_RELEASE_REPO,
        "--limit",
        "50",
        "--json",
        "tagName",
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=CREATE_NO_WINDOW,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        items = json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None

    pattern = re.compile(rf"^{re.escape(app_slug)}-v(\d+)\.(\d+)\.(\d+)")
    versions: list[tuple[int, int, int]] = []
    for entry in items:
        tag = str(entry.get("tagName", ""))
        match = pattern.match(tag)
        if match:
            versions.append((int(match.group(1)), int(match.group(2)), int(match.group(3))))
    return max(versions) if versions else None


def suggest_tag(repo_name: str, target: str) -> str:
    """Suggest date-based tag for private/self, or auto-incremented SemVer for MSKLabsApps."""
    if target == "msklabsapps":
        slug = to_app_slug(repo_name)
        latest = fetch_latest_public_version(slug)
        if latest is None:
            return f"{slug}-v1.0.0"
        major, minor, patch = latest
        return f"{slug}-v{major}.{minor}.{patch + 1}"

    stamp = datetime.now().strftime("%y.%m.%d-%H.%M")
    return f"v{stamp}"


def _strip_repo_prefix(repo_name: str) -> str:
    """Remove M_/D_/W_ prefix and keep clean display name for release filenames."""
    cleaned = re.sub(r"^[a-zA-Z]_", "", repo_name.strip())
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "", cleaned)
    return cleaned or "App"


def _extract_version_part(repo_name: str, tag: str) -> str:
    """Extract version suffix from tag (e.g., rekatsay-v1.3.1 -> v1.3.1)."""
    clean_tag = tag.strip()
    for candidate in (repo_name, _strip_repo_prefix(repo_name)):
        prefix = f"{to_app_slug(candidate)}-"
        if clean_tag.startswith(prefix):
            return clean_tag[len(prefix):]
    return clean_tag


def _is_generic_binary_name(filename: str, repo_name: str) -> bool:
    """Return True if filename is generic (e.g., app-release.apk) or lacks app identity."""
    stem_low = Path(filename).stem.lower()
    if stem_low in {"app-release", "app", "release", "app-debug", "main", "output"}:
        return True
    app_tok = _norm_token(repo_name)
    return bool(app_tok) and app_tok not in _norm_token(stem_low)


def build_standard_binary_name(repo_name: str, tag: str, ext: str) -> str:
    """Build `<AppName>-<version><ext>` filename per IST-015."""
    app_label = _strip_repo_prefix(repo_name)
    ver = _extract_version_part(repo_name, tag)
    suffix = ext if ext.startswith(".") else f".{ext}" if ext else ""
    return f"{app_label}-{ver}{suffix}"


def upload_release(
    target_repo: str,
    tag: str,
    file_path: str,
    title: str = "",
    notes: str = "",
    repo_name: str = "",
) -> tuple[bool, str]:
    """Upload a compiled binary to GitHub Releases via `gh release create` with IST-015 naming."""
    artifact = Path(file_path)
    if not artifact.is_file():
        return False, f"Dosya bulunamadı: {file_path}"

    app_name = repo_name.strip() or target_repo.strip().split("/")[-1]
    release_title = title.strip() or f"{_strip_repo_prefix(app_name)} ({tag})"

    with tempfile.TemporaryDirectory() as tmp_dir:
        upload_path = artifact
        if _is_generic_binary_name(artifact.name, app_name):
            std_name = build_standard_binary_name(app_name, tag, artifact.suffix)
            upload_path = Path(tmp_dir) / std_name
            shutil.copy2(artifact, upload_path)

        cmd = [
            "gh",
            "release",
            "create",
            tag.strip(),
            str(upload_path),
            "-R",
            target_repo.strip(),
            "--title",
            release_title,
            "--notes",
            notes.strip() or f"Yükleme tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ]

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                creationflags=CREATE_NO_WINDOW,
            )
        except FileNotFoundError:
            return False, "Sistemde 'gh' (GitHub CLI) bulunamadı."
        except subprocess.TimeoutExpired:
            return False, "Release yükleme zaman aşımına uğradı (300s)."
        except OSError as exc:
            return False, f"Release yükleme hatası: {exc}"

    if completed.returncode == 0:
        url = (completed.stdout or "").strip().splitlines()[-1] if completed.stdout.strip() else ""
        return True, url or "Release başarıyla yüklendi."

    err = (completed.stderr or completed.stdout or "Bilinmeyen gh hatası").strip()
    return False, err


def find_latest_release_tag(
    repo_name: str,
    target_repo: str,
    is_public_catalog: bool,
) -> str | None:
    """Find the most recent release tag on target_repo for this app."""
    limit = "50" if is_public_catalog else "1"
    cmd = [
        "gh",
        "release",
        "list",
        "-R",
        target_repo.strip(),
        "--limit",
        limit,
        "--json",
        "tagName",
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            creationflags=CREATE_NO_WINDOW,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        items = json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None

    if not items:
        return None

    if not is_public_catalog:
        return str(items[0].get("tagName", "")).strip() or None

    slug = to_app_slug(repo_name)
    prefix = f"{slug}-v"
    for entry in items:
        tag = str(entry.get("tagName", "")).strip()
        if tag.startswith(prefix):
            return tag
    return None


def _get_gh_token() -> str | None:
    try:
        completed = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
        if completed.returncode == 0:
            return completed.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _get_release_assets(tag: str, target_repo: str) -> list[dict]:
    cmd = ["gh", "release", "view", tag, "-R", target_repo, "--json", "assets"]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            creationflags=CREATE_NO_WINDOW,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return []
        data = json.loads(completed.stdout)
        return list(data.get("assets", []))
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def _build_cloudflare_candidates(
    repo_name: str,
    tag: str,
    asset_name: str,
) -> list[str]:
    """Build ordered Cloudflare Worker (/dl/) and R2 (releases.msklabs.org) URLs."""
    slug = to_app_slug(repo_name)
    slug_variants = [slug]
    if "-" in slug:
        slug_variants.append(slug.replace("-", "_"))

    prefix = f"{slug}-"
    version = tag[len(prefix):] if tag.startswith(prefix) else tag

    urls: list[str] = []
    for s in slug_variants:
        urls.append(f"{CF_DL_BASE}/{s}/{version}")
        urls.append(f"{CF_R2_BASE}/{s}/{version}/{asset_name}")
    return urls


def _stream_url_to_file(
    url: str,
    final_path: Path,
    headers: dict[str, str],
    expected_size: int = 0,
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[bool, str]:
    """Download a URL to a .part file and atomically rename on completion."""
    part_path = final_path.with_name(f"{final_path.name}.part")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total_size = expected_size or int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            with part_path.open("wb") as out_f:
                while True:
                    chunk = resp.read(262144)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb is not None:
                        progress_cb(downloaded, total_size)
        part_path.replace(final_path)
        return True, str(final_path)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        part_path.unlink(missing_ok=True)
        return False, str(exc)


def download_latest_release(
    repo_name: str,
    repo_path: str | Path,
    target: str,
    dest_dir: str,
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[bool, str, str]:
    """Stream the latest release asset into dest_dir (Cloudflare CDN first for public, GitHub fallback)."""
    if target == "msklabsapps":
        target_repo = PUBLIC_RELEASE_REPO
        is_public = True
    else:
        target_repo = detect_repo_slug(repo_path) or ""
        is_public = False

    if not target_repo:
        return False, "", "Bu repoda GitHub 'origin' remote adresi tanımlı değil."

    tag = find_latest_release_tag(repo_name, target_repo, is_public)
    if not tag:
        return False, "", f"{target_repo} üzerinde uygun release bulunamadı."

    assets = _get_release_assets(tag, target_repo)
    if not assets:
        return False, tag, f"{tag} içinde indirilebilir dosya bulunamadı."

    asset = assets[0]
    asset_name = str(asset.get("name") or f"{tag}.bin")
    total_size = int(asset.get("size") or 0)
    api_url = str(asset.get("apiUrl") or asset.get("url") or "")
    if not api_url:
        return False, tag, "Release dosya adresi alınamadı."

    out_dir = Path(dest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    local_name = (
        build_standard_binary_name(repo_name, tag, Path(asset_name).suffix or ".bin")
        if _is_generic_binary_name(asset_name, repo_name)
        else asset_name
    )
    final_path = out_dir / local_name

    if is_public:
        cf_headers = {"User-Agent": "PushPull"}
        for cf_url in _build_cloudflare_candidates(repo_name, tag, asset_name):
            ok, msg = _stream_url_to_file(
                cf_url,
                final_path,
                cf_headers,
                expected_size=total_size,
                progress_cb=progress_cb,
            )
            if ok:
                return True, tag, f"{msg} (Cloudflare CDN)"

    gh_headers = {
        "User-Agent": "PushPull",
        "Accept": "application/octet-stream",
    }
    token = _get_gh_token()
    if token:
        gh_headers["Authorization"] = f"Bearer {token}"

    ok, msg = _stream_url_to_file(
        api_url,
        final_path,
        gh_headers,
        expected_size=total_size,
        progress_cb=progress_cb,
    )
    if ok:
        return True, tag, f"{msg} (GitHub)"
    return False, tag, f"İndirme hatası: {msg}"
