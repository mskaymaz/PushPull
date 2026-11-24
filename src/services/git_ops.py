"""High-level Git operations returning structured RepoRunResult objects."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.models.repo_models import RepoRunResult, RepoStatus
from src.services.git_runner import GitCommandResult, run_git


def _result_logs(step: str, cmd_res: GitCommandResult) -> list[str]:
    """Format a GitCommandResult into readable log lines."""
    cmd_str = " ".join(cmd_res.command)
    lines = [f"[{step.upper()}] $ {cmd_str}"]
    output = cmd_res.combined_output
    if output:
        lines.extend(output.splitlines())
    else:
        lines.append("(çıktı yok)" if cmd_res.ok else f"(exit code: {cmd_res.returncode})")
    return lines


def _parse_porcelain_v2(output: str) -> tuple[str, int, int, int]:
    """Parse `git status --porcelain=v2 --branch` into (branch, ahead, behind, dirty_count)."""
    branch = ""
    ahead = 0
    behind = 0
    dirty_count = 0

    for line in output.splitlines():
        if line.startswith("# branch.head "):
            branch = line.removeprefix("# branch.head ").strip()
        elif line.startswith("# branch.ab "):
            parts = line.removeprefix("# branch.ab ").strip().split()
            for part in parts:
                if part.startswith("+"):
                    ahead = int(part[1:])
                elif part.startswith("-"):
                    behind = int(part[1:])
        elif line and not line.startswith("#"):
            dirty_count += 1

    return branch, ahead, behind, dirty_count


def fetch(repo_path: str | Path) -> RepoRunResult:
    """Fetch remote updates with pruning."""
    path_str = str(repo_path)
    res = run_git(path_str, ["fetch", "--prune"])
    return RepoRunResult(
        repo_path=path_str,
        step="fetch",
        success=res.ok,
        status=RepoStatus.SUCCESS if res.ok else RepoStatus.ERROR,
        message="Fetch tamamlandı" if res.ok else "Fetch başarısız",
        logs=_result_logs("fetch", res),
    )


def analyze(repo_path: str | Path) -> RepoRunResult:
    """Analyze current branch, ahead/behind counts, and dirty file count."""
    path_str = str(repo_path)
    res = run_git(path_str, ["status", "--porcelain=v2", "--branch"])
    if not res.ok:
        return RepoRunResult(
            repo_path=path_str,
            step="analyze",
            success=False,
            status=RepoStatus.ERROR,
            message="Analiz başarısız",
            logs=_result_logs("analyze", res),
        )

    branch, ahead, behind, dirty_count = _parse_porcelain_v2(res.stdout)
    status = RepoStatus.WARNING if (dirty_count > 0 or behind > 0) else RepoStatus.SUCCESS
    dirty_label = f"Kirli: {dirty_count}" if dirty_count > 0 else "Temiz"
    summary = f"{branch or 'HEAD'} | ↑{ahead} ↓{behind} | {dirty_label}"

    return RepoRunResult(
        repo_path=path_str,
        step="analyze",
        success=True,
        status=status,
        message=summary,
        logs=_result_logs("analyze", res),
        ahead=ahead,
        behind=behind,
        dirty_count=dirty_count,
        branch=branch,
    )


def stash(repo_path: str | Path) -> RepoRunResult:
    """Stash local changes (including untracked files) if working tree is dirty."""
    path_str = str(repo_path)
    check = run_git(path_str, ["status", "--porcelain"])
    if not check.ok:
        return RepoRunResult(
            repo_path=path_str,
            step="stash",
            success=False,
            status=RepoStatus.ERROR,
            message="Stash durum kontrolü başarısız",
            logs=_result_logs("stash", check),
        )

    if not check.stdout.strip():
        return RepoRunResult(
            repo_path=path_str,
            step="stash",
            success=True,
            status=RepoStatus.SUCCESS,
            message="Çalışma ağacı temiz, stash atlandı",
            logs=["[STASH] Çalışma ağacı temiz, stash gerekmedi."],
        )

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    res = run_git(path_str, ["stash", "push", "-u", "-m", f"PushPull auto-stash {stamp}"])
    return RepoRunResult(
        repo_path=path_str,
        step="stash",
        success=res.ok,
        status=RepoStatus.SUCCESS if res.ok else RepoStatus.ERROR,
        message="Değişiklikler stash edildi" if res.ok else "Stash başarısız",
        logs=_result_logs("stash", res),
    )


def pull(repo_path: str | Path) -> RepoRunResult:
    """Pull updates from the tracked upstream branch."""
    path_str = str(repo_path)
    res = run_git(path_str, ["pull"])
    return RepoRunResult(
        repo_path=path_str,
        step="pull",
        success=res.ok,
        status=RepoStatus.SUCCESS if res.ok else RepoStatus.ERROR,
        message="Pull tamamlandı" if res.ok else "Pull başarısız",
        logs=_result_logs("pull", res),
    )


def commit(repo_path: str | Path, message: str = "") -> RepoRunResult:
    """Stage all changes and commit; auto-generates timestamp message if empty."""
    path_str = str(repo_path)
    check = run_git(path_str, ["status", "--porcelain"])
    if not check.ok:
        return RepoRunResult(
            repo_path=path_str,
            step="commit",
            success=False,
            status=RepoStatus.ERROR,
            message="Commit durum kontrolü başarısız",
            logs=_result_logs("commit", check),
        )

    if not check.stdout.strip():
        return RepoRunResult(
            repo_path=path_str,
            step="commit",
            success=True,
            status=RepoStatus.SUCCESS,
            message="Commitlenecek değişiklik yok",
            logs=["[COMMIT] Çalışma ağacı temiz, commit atlandı."],
        )

    add_res = run_git(path_str, ["add", "-A"])
    logs = _result_logs("commit-add", add_res)
    if not add_res.ok:
        return RepoRunResult(
            repo_path=path_str,
            step="commit",
            success=False,
            status=RepoStatus.ERROR,
            message="Dosyalar stage edilemedi",
            logs=logs,
        )

    stamp = datetime.now().strftime("%y.%m.%d_%H.%M")
    user_note = message.strip()
    commit_msg = f"{user_note} {stamp}" if user_note else stamp
    commit_res = run_git(path_str, ["commit", "-m", commit_msg])
    logs.extend(_result_logs("commit", commit_res))
    return RepoRunResult(
        repo_path=path_str,
        step="commit",
        success=commit_res.ok,
        status=RepoStatus.SUCCESS if commit_res.ok else RepoStatus.ERROR,
        message=f"Commit tamamlandı: {commit_msg}" if commit_res.ok else "Commit başarısız",
        logs=logs,
    )


def push(repo_path: str | Path) -> RepoRunResult:
    """Push local commits to the remote repository."""
    path_str = str(repo_path)
    res = run_git(path_str, ["push"])
    return RepoRunResult(
        repo_path=path_str,
        step="push",
        success=res.ok,
        status=RepoStatus.SUCCESS if res.ok else RepoStatus.ERROR,
        message="Push tamamlandı" if res.ok else "Push başarısız",
        logs=_result_logs("push", res),
    )
