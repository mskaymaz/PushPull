"""Asynchronous QRunnable worker for executing per-repo Git pipelines."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, Signal

from src.models.repo_models import RepoRunResult, RepoStatus
from src.services import git_ops

PIPELINE_ORDER = ("fetch", "analyze", "stash", "pull", "commit", "push")


@dataclass
class PipelineOptions:
    """Selected Git steps and commit message for a single repository run."""

    fetch: bool = False
    analyze: bool = False
    stash: bool = False
    pull: bool = False
    commit: bool = False
    push: bool = False
    commit_message: str = ""

    def selected_steps(self) -> list[str]:
        """Return enabled steps in the fixed safe execution order."""
        return [step for step in PIPELINE_ORDER if getattr(self, step)]


class RepoWorkerSignals(QObject):
    """Qt signals emitted by RepoWorker for row-level UI updates."""

    started = Signal(str)
    step_done = Signal(str, object)
    finished = Signal(str, object)
    error = Signal(str, object)


class RepoWorker(QRunnable):
    """Executes selected Git operations sequentially for one repository."""

    def __init__(self, repo_path: str, options: PipelineOptions) -> None:
        super().__init__()
        self.repo_path = repo_path
        self.options = options
        self.signals = RepoWorkerSignals()

    def run(self) -> None:
        """Run selected steps in fixed order; stop immediately on failure."""
        self.signals.started.emit(self.repo_path)
        steps = self.options.selected_steps()
        if not steps:
            empty_result = RepoRunResult(
                repo_path=self.repo_path,
                step="idle",
                success=True,
                status=RepoStatus.IDLE,
                message="Çalıştırılacak adım seçilmedi",
            )
            self.signals.finished.emit(self.repo_path, empty_result)
            return

        last_result: RepoRunResult | None = None
        for step in steps:
            result = self._execute_step(step)
            last_result = result
            if not result.success:
                self.signals.error.emit(self.repo_path, result)
                return
            self.signals.step_done.emit(self.repo_path, result)

        if last_result is not None:
            self.signals.finished.emit(self.repo_path, last_result)

    def _execute_step(self, step: str) -> RepoRunResult:
        if step == "fetch":
            return git_ops.fetch(self.repo_path)
        if step == "analyze":
            return git_ops.analyze(self.repo_path)
        if step == "stash":
            return git_ops.stash(self.repo_path)
        if step == "pull":
            if not self.options.stash:
                status_check = git_ops.analyze(self.repo_path)
                if not status_check.success:
                    return status_check
                if status_check.dirty_count > 0:
                    return RepoRunResult(
                        repo_path=self.repo_path,
                        step="pull",
                        success=False,
                        status=RepoStatus.WARNING,
                        message="Güvenlik: Kirli ağaçta Stash seçilmeden Pull engellendi",
                        logs=[
                            "[GÜVENLİK ENGELİ] Çalışma ağacında commitlenmemiş değişiklikler var "
                            f"({status_check.dirty_count} dosya). Pull öncesi 'Stash' seçin "
                            "veya değişiklikleri commit'leyin."
                        ],
                    )
            return git_ops.pull(self.repo_path)
        if step == "commit":
            return git_ops.commit(self.repo_path, self.options.commit_message)
        if step == "push":
            return git_ops.push(self.repo_path)

        return RepoRunResult(
            repo_path=self.repo_path,
            step=step,
            success=False,
            status=RepoStatus.ERROR,
            message=f"Bilinmeyen adım: {step}",
        )
