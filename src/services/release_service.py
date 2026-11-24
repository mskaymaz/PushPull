"""GitHub Releases upload helpers powered by GitHub CLI (`gh`)."""

from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.services.git_runner import CREATE_NO_WINDOW, run_git

PUBLIC_RELEASE_REPO = "mskaymaz/MSKLabsApps"


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


def suggest_artifact(repo_path: str | Path) -> str:
    """Return the first likely compiled binary (.exe or .apk) inside repo_path."""
    root = Path(repo_path)
    candidates = [
        *(root / "dist").glob("*.exe"),
        *(root / "build" / "app" / "outputs" / "flutter-apk").glob("*.apk"),
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return ""


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


def upload_release(
    target_repo: str,
    tag: str,
    file_path: str,
    title: str = "",
    notes: str = "",
) -> tuple[bool, str]:
    """Upload a compiled binary to GitHub Releases via `gh release create`."""
    artifact = Path(file_path)
    if not artifact.is_file():
        return False, f"Dosya bulunamadı: {file_path}"

    release_title = title.strip() or f"{artifact.stem} ({tag})"
    cmd = [
        "gh",
        "release",
        "create",
        tag.strip(),
        str(artifact),
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


def download_latest_release(
    repo_name: str,
    repo_path: str | Path,
    target: str,
    dest_dir: str,
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[bool, str, str]:
    """Stream the latest release asset into dest_dir with live byte progress."""
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
    final_path = out_dir / asset_name
    part_path = out_dir / f"{asset_name}.part"

    headers = {
        "User-Agent": "PushPull",
        "Accept": "application/octet-stream",
    }
    token = _get_gh_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            if total_size <= 0:
                total_size = int(resp.headers.get("Content-Length") or 0)
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
        return True, tag, f"{final_path}"
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        part_path.unlink(missing_ok=True)
        return False, tag, f"İndirme hatası: {exc}"
