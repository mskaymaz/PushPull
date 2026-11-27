"""Persistence service for tracked repositories in repos.json."""

from __future__ import annotations

import json
import os
import shutil
import socket
import sys
from pathlib import Path
from typing import Any

from src.models.repo_models import MAX_HISTORY_PER_REPO, RepoItem, RepoRunRecord
from src.services.git_runner import run_git


def _default_config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return base / "MSKLabs" / "PushPull" / "repos.json"


DEFAULT_CONFIG_PATH = _default_config_path()


def _normalize_path(path: str) -> str:
    """Normalize a repository path for consistent comparison on Windows."""
    if not path.strip():
        return ""
    return os.path.normcase(str(Path(path).expanduser().resolve()))


def _detect_remote_url(repo_path: str | Path) -> str:
    res = run_git(repo_path, ["remote", "get-url", "origin"])
    return res.stdout.strip() if res.ok else ""


def _repo_identity_key(repo: RepoItem) -> str:
    if repo.remote_url.strip():
        return repo.remote_url.strip().rstrip(".git").casefold()
    return repo.name.strip().casefold()


class ConfigStore:
    """Reads and writes the repository list, host paths, and sync metadata to repos.json."""

    def __init__(self, config_path: Path | str = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = Path(config_path)
        if self.config_path == DEFAULT_CONFIG_PATH and not self.config_path.exists():
            self._migrate_legacy_config()

    def _migrate_legacy_config(self) -> None:
        """One-time migration from exe/cwd repos.json into LocalAppData."""
        candidates = (
            [Path(sys.executable).parent / "repos.json", Path("repos.json")]
            if getattr(sys, "frozen", False)
            else [Path("repos.json")]
        )
        for legacy in candidates:
            if legacy.is_file():
                try:
                    self.config_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(legacy, self.config_path)
                except OSError:
                    pass
                break

    def _read_raw(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def load_gist_id(self) -> str | None:
        """Return cached Secret Gist ID from repos.json, if present."""
        gid = self._read_raw().get("gist_id")
        return str(gid).strip() if gid else None

    def save_gist_id(self, gist_id: str) -> None:
        """Persist Secret Gist ID alongside repositories in repos.json."""
        repos = self.load_repos()
        self._write_raw(repos, gist_id=gist_id)

    def load_repos(self) -> list[RepoItem]:
        """Load repositories from JSON, sorted and re-indexed by order."""
        payload = self._read_raw()
        raw_items = payload.get("repos", [])
        items: list[RepoItem] = []
        for idx, entry in enumerate(raw_items):
            if isinstance(entry, dict) and (entry.get("path") or entry.get("name")):
                items.append(RepoItem.from_dict(entry, default_order=idx))

        items.sort(key=lambda item: item.order)
        self._reindex(items)
        return items

    def save_repos(self, repos: list[RepoItem]) -> None:
        """Persist repositories and their sequential order to JSON."""
        self._write_raw(repos, gist_id=self.load_gist_id())

    def _write_raw(self, repos: list[RepoItem], gist_id: str | None) -> None:
        self._reindex(repos)
        data: dict[str, Any] = {
            "gist_id": gist_id or "",
            "repos": [repo.to_dict() for repo in repos],
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.config_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(self.config_path)

    def add_repo(self, path: str, name: str | None = None) -> list[RepoItem]:
        """Add a repository if not already tracked, then save."""
        repos = self.load_repos()
        target_norm = _normalize_path(path)
        if any(_normalize_path(r.path) == target_norm for r in repos):
            return repos

        resolved = str(Path(path).expanduser().resolve())
        repo_name = (name or Path(resolved).name).strip() or "repo"
        host = socket.gethostname()
        remote_url = _detect_remote_url(resolved)
        repos.append(
            RepoItem(
                name=repo_name,
                path=resolved,
                order=len(repos),
                remote_url=remote_url,
                paths_by_host={host: resolved},
            )
        )
        self.save_repos(repos)
        return repos

    def remove_repo(self, path: str) -> list[RepoItem]:
        """Remove a repository by path, re-index order, and save."""
        repos = self.load_repos()
        target_norm = _normalize_path(path)
        filtered = [r for r in repos if _normalize_path(r.path) != target_norm]
        if len(filtered) != len(repos):
            self.save_repos(filtered)
        return filtered

    def move_repo(self, index: int, direction: int) -> list[RepoItem]:
        """Move a repository up (direction=-1) or down (direction=+1) and save."""
        repos = self.load_repos()
        target_index = index + direction
        if not (0 <= index < len(repos) and 0 <= target_index < len(repos)):
            return repos

        repos[index], repos[target_index] = repos[target_index], repos[index]
        self.save_repos(repos)
        return repos

    def append_run_record(self, repo_path: str, record: RepoRunRecord) -> list[RepoItem]:
        """Prepend a run record to a repository's history (max 5) and save."""
        repos = self.load_repos()
        target_norm = _normalize_path(repo_path)
        for repo in repos:
            if _normalize_path(repo.path) == target_norm:
                repo.history = [record, *repo.history][:MAX_HISTORY_PER_REPO]
                break
        self.save_repos(repos)
        return repos

    def promote_repos_to_top(self, repo_paths: list[str]) -> list[RepoItem]:
        """Move executed repositories to the top, sorted alphabetically by name."""
        if not repo_paths:
            return self.load_repos()

        repos = self.load_repos()
        target_norms = {_normalize_path(p) for p in repo_paths}
        promoted = [r for r in repos if _normalize_path(r.path) in target_norms]
        rest = [r for r in repos if _normalize_path(r.path) not in target_norms]
        promoted.sort(key=lambda r: r.name.casefold())

        reordered = promoted + rest
        self.save_repos(reordered)
        return reordered

    def set_release_target(
        self,
        repo_path: str,
        target: str,
        release_dir: str = "",
    ) -> list[RepoItem]:
        """Persist the release target and last release directory for a repository."""
        repos = self.load_repos()
        target_norm = _normalize_path(repo_path)
        for repo in repos:
            if _normalize_path(repo.path) == target_norm:
                repo.release_target = target if target in ("self", "msklabsapps") else ""
                if release_dir.strip():
                    repo.release_dir = release_dir.strip()
                break
        self.save_repos(repos)
        return repos

    def remap_repo_path(self, old_path: str, new_path: str) -> list[RepoItem]:
        """Update the local folder path for the current hostname."""
        repos = self.load_repos()
        resolved = str(Path(new_path).expanduser().resolve())
        host = socket.gethostname()
        old_norm = _normalize_path(old_path)
        for repo in repos:
            if _normalize_path(repo.path) == old_norm or repo.path == old_path:
                repo.path = resolved
                repo.paths_by_host[host] = resolved
                if not repo.remote_url:
                    repo.remote_url = _detect_remote_url(resolved)
                break
        self.save_repos(repos)
        return repos

    def scan_and_map_folder(self, root_folder: str) -> tuple[int, list[RepoItem]]:
        """Scan root_folder (depth<=3) for Git repos and map paths for this host."""
        root = Path(root_folder).expanduser().resolve()
        if not root.is_dir():
            return 0, self.load_repos()

        discovered: list[tuple[str, str, str]] = []
        self._collect_git_repos(root, depth=0, max_depth=3, out=discovered)

        by_remote = {remote.rstrip(".git").casefold(): path for path, _, remote in discovered if remote}
        by_name = {name.casefold(): path for path, name, _ in discovered}

        host = socket.gethostname()
        repos = self.load_repos()
        matched = 0
        for repo in repos:
            if Path(repo.path).exists():
                continue
            remote_key = repo.remote_url.strip().rstrip(".git").casefold()
            new_path = by_remote.get(remote_key) if remote_key else None
            if not new_path:
                new_path = by_name.get(repo.name.strip().casefold())
            if new_path:
                repo.path = new_path
                repo.paths_by_host[host] = new_path
                matched += 1

        if matched > 0:
            self.save_repos(repos)
        return matched, repos

    def _collect_git_repos(
        self,
        folder: Path,
        depth: int,
        max_depth: int,
        out: list[tuple[str, str, str]],
    ) -> None:
        if (folder / ".git").exists():
            out.append((str(folder), folder.name, _detect_remote_url(folder)))
            return
        if depth >= max_depth:
            return
        try:
            for child in folder.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    self._collect_git_repos(child, depth + 1, max_depth, out)
        except OSError:
            pass

    def export_sync_payload(self) -> dict[str, Any]:
        """Build lightweight JSON payload for Secret Gist synchronization."""
        repos = self.load_repos()
        return {"repos": [repo.to_sync_dict() for repo in repos]}

    def merge_remote_payload(self, payload: dict[str, Any]) -> list[RepoItem]:
        """Merge remote Gist repo list while preserving local run history."""
        local_repos = self.load_repos()
        local_by_key = {_repo_identity_key(r): r for r in local_repos}
        host = socket.gethostname()

        merged: list[RepoItem] = []
        raw_items = payload.get("repos", [])
        for idx, entry in enumerate(raw_items):
            if not isinstance(entry, dict):
                continue
            remote_item = RepoItem.from_dict(entry, default_order=idx)
            key = _repo_identity_key(remote_item)
            local_match = local_by_key.get(key)
            if local_match is not None:
                remote_item.history = local_match.history
                remote_item.release_dir = local_match.release_dir
                if host in local_match.paths_by_host:
                    remote_item.paths_by_host[host] = local_match.paths_by_host[host]
                    remote_item.path = local_match.paths_by_host[host]
                elif local_match.path and Path(local_match.path).exists():
                    remote_item.path = local_match.path
                    remote_item.paths_by_host[host] = local_match.path
            merged.append(remote_item)

        self.save_repos(merged)
        return merged

    @staticmethod
    def _reindex(repos: list[RepoItem]) -> None:
        for idx, repo in enumerate(repos):
            repo.order = idx
