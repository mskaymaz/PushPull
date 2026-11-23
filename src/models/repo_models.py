"""Data models for repository items and execution results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class RepoStatus(str, Enum):
    """Execution and health status of a repository row."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class RepoItem:
    """Represents a tracked Git repository in the PushPull list."""

    name: str
    path: str
    order: int = 0
    status: RepoStatus = RepoStatus.IDLE
    logs: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    dirty_count: int = 0
    branch: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize persistent fields for repos.json storage."""
        return {
            "name": self.name,
            "path": self.path,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], default_order: int = 0) -> RepoItem:
        """Create a RepoItem from a serialized dictionary."""
        raw_path = str(data.get("path", "")).strip()
        fallback_name = Path(raw_path).name if raw_path else "repo"
        name = str(data.get("name") or fallback_name).strip()
        order = int(data.get("order", default_order))
        return cls(name=name, path=raw_path, order=order)


@dataclass
class RepoRunResult:
    """Result returned by a Git step or full pipeline run for a repository."""

    repo_path: str
    step: str
    success: bool
    status: RepoStatus = RepoStatus.IDLE
    message: str = ""
    logs: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    dirty_count: int = 0
    branch: str = ""
