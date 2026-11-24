"""GitHub Releases upload helpers powered by GitHub CLI (`gh`)."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

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
