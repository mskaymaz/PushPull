"""Cloud synchronization of PushPull repository settings via a Secret GitHub Gist."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.services.git_runner import CREATE_NO_WINDOW

SYNC_GIST_DESCRIPTION = "PushPull Sync Config"
SYNC_GIST_FILENAME = "pushpull-sync.json"


def _run_gh(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def find_sync_gist_id() -> str | None:
    """Locate the Secret Gist matching SYNC_GIST_DESCRIPTION."""
    res = _run_gh(["gist", "list", "--secret", "--limit", "50"])
    if res is None or res.returncode != 0:
        return None

    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].strip() == SYNC_GIST_DESCRIPTION:
            return parts[0].strip()
    return None


def pull_sync_payload(gist_id: str | None = None) -> tuple[str | None, dict[str, Any] | None]:
    """Fetch the remote sync JSON payload from the user's Secret Gist."""
    gid = gist_id or find_sync_gist_id()
    if not gid:
        return None, None

    res = _run_gh(["gist", "view", gid, "-f", SYNC_GIST_FILENAME, "-r"])
    if res is None or res.returncode != 0 or not res.stdout.strip():
        return gid, None

    try:
        payload = json.loads(res.stdout)
        return gid, payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return gid, None


def push_sync_payload(
    payload: dict[str, Any],
    gist_id: str | None = None,
) -> tuple[bool, str | None]:
    """Create or update the Secret Gist with the latest repository sync payload."""
    gid = gist_id or find_sync_gist_id()
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_file = tmp_dir / SYNC_GIST_FILENAME
    tmp_file.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    try:
        if gid:
            res = _run_gh(["gist", "edit", gid, str(tmp_file)])
            ok = res is not None and res.returncode == 0
            return ok, gid

        res = _run_gh(
            ["gist", "create", str(tmp_file), "-d", SYNC_GIST_DESCRIPTION]
        )
        if res is not None and res.returncode == 0:
            url = (res.stdout or "").strip().splitlines()[-1]
            new_id = url.rstrip("/").split("/")[-1]
            return True, new_id
        return False, None
    finally:
        tmp_file.unlink(missing_ok=True)
        tmp_dir.rmdir()
