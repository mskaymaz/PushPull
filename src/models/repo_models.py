"""Data models for repository items, run history records, and execution results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

MAX_HISTORY_PER_REPO = 5


class RepoStatus(str, Enum):
    """Execution and health status of a repository row."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class RepoRunRecord:
    """Single run-history entry representing one execution batch on a repository."""

    timestamp: str
    steps: list[str]
    status: RepoStatus
    summary: str
    logs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize run record for repos.json persistence."""
        return {
            "timestamp": self.timestamp,
            "steps": list(self.steps),
            "status": self.status.value,
            "summary": self.summary,
            "logs": list(self.logs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoRunRecord:
        """Deserialize a RepoRunRecord from JSON data."""
        raw_status = str(data.get("status", RepoStatus.IDLE.value))
        try:
            status = RepoStatus(raw_status)
        except ValueError:
            status = RepoStatus.IDLE

        return cls(
            timestamp=str(data.get("timestamp", "")),
            steps=[str(s) for s in data.get("steps", [])],
            status=status,
            summary=str(data.get("summary", "")),
            logs=[str(line) for line in data.get("logs", [])],
        )


@dataclass
class RepoItem:
    """Represents a tracked Git repository in the PushPull list."""

    name: str
    path: str
    order: int = 0
    status: RepoStatus = RepoStatus.IDLE
    logs: list[str] = field(default_factory=list)
    history: list[RepoRunRecord] = field(default_factory=list)
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
            "history": [rec.to_dict() for rec in self.history[:MAX_HISTORY_PER_REPO]],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], default_order: int = 0) -> RepoItem:
        """Create a RepoItem from a serialized dictionary."""
        raw_path = str(data.get("path", "")).strip()
        fallback_name = Path(raw_path).name if raw_path else "repo"
        name = str(data.get("name") or fallback_name).strip()
        order = int(data.get("order", default_order))
        raw_history = data.get("history", [])
        history = [
            RepoRunRecord.from_dict(entry)
            for entry in raw_history[:MAX_HISTORY_PER_REPO]
            if isinstance(entry, dict)
        ]
        return cls(name=name, path=raw_path, order=order, history=history)


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
