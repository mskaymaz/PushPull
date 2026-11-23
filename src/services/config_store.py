"""Persistence service for tracked repositories in repos.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from src.models.repo_models import MAX_HISTORY_PER_REPO, RepoItem, RepoRunRecord

DEFAULT_CONFIG_PATH = (
    Path(sys.executable).parent / "repos.json"
    if getattr(sys, "frozen", False)
    else Path("repos.json")
)


def _normalize_path(path: str) -> str:
    """Normalize a repository path for consistent comparison on Windows."""
    return os.path.normcase(str(Path(path).expanduser().resolve()))


class ConfigStore:
    """Reads and writes the repository list and display order to repos.json."""

    def __init__(self, config_path: Path | str = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = Path(config_path)

    def load_repos(self) -> list[RepoItem]:
        """Load repositories from JSON, sorted and re-indexed by order."""
        if not self.config_path.exists():
            return []

        try:
            raw_text = self.config_path.read_text(encoding="utf-8")
            payload: Any = json.loads(raw_text)
        except (OSError, json.JSONDecodeError):
            return []

        raw_items = payload.get("repos", []) if isinstance(payload, dict) else []
        items: list[RepoItem] = []
        for idx, entry in enumerate(raw_items):
            if isinstance(entry, dict) and entry.get("path"):
                items.append(RepoItem.from_dict(entry, default_order=idx))

        items.sort(key=lambda item: item.order)
        self._reindex(items)
        return items

    def save_repos(self, repos: list[RepoItem]) -> None:
        """Persist repositories and their sequential order to JSON."""
        self._reindex(repos)
        data = {"repos": [repo.to_dict() for repo in repos]}
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
        repos.append(RepoItem(name=repo_name, path=resolved, order=len(repos)))
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

    @staticmethod
    def _reindex(repos: list[RepoItem]) -> None:
        for idx, repo in enumerate(repos):
            repo.order = idx
