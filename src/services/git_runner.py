"""Low-level subprocess wrapper for executing Git CLI commands safely."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


@dataclass
class GitCommandResult:
    """Structured output from a single Git CLI invocation."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        """Return True when the command exited with status 0."""
        return self.returncode == 0

    @property
    def combined_output(self) -> str:
        """Return non-empty stdout and stderr combined cleanly."""
        parts = [part.strip() for part in (self.stdout, self.stderr) if part.strip()]
        return "\n".join(parts)


def run_git(
    repo_path: str | Path,
    args: list[str],
    timeout: int = 120,
) -> GitCommandResult:
    """Execute a git command in repo_path without opening a console window."""
    cmd = ["git", *args]
    cwd = Path(repo_path)
    if not cwd.exists():
        return GitCommandResult(
            command=cmd,
            returncode=-1,
            stdout="",
            stderr=f"Klasör bulunamadı: {cwd}",
        )

    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
            env=env,
        )
        return GitCommandResult(
            command=cmd,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )
    except subprocess.TimeoutExpired:
        return GitCommandResult(
            command=cmd,
            returncode=-1,
            stdout="",
            stderr=f"Komut zaman aşımına uğradı ({timeout}s): {' '.join(cmd)}",
        )
    except FileNotFoundError:
        return GitCommandResult(
            command=cmd,
            returncode=-1,
            stdout="",
            stderr="Sistemde 'git' komutu bulunamadı.",
        )
    except OSError as exc:
        return GitCommandResult(
            command=cmd,
            returncode=-1,
            stdout="",
            stderr=f"Komut çalıştırma hatası: {exc}",
        )
