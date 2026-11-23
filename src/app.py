"""Application entry point for PushPull."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from src.models.repo_models import RepoItem, RepoRunRecord, RepoRunResult, RepoStatus
from src.services.config_store import ConfigStore, DEFAULT_CONFIG_PATH
from src.services.repo_worker import PipelineOptions, RepoWorker
from src.ui.repo_list import RepoListWidget
from src.ui.repo_row import RepoRowWidget
from src.ui.styles import APP_STYLESHEET
from src.ui.toolbar import TopToolbar


class MainWindow(QMainWindow):
    """Main application window for PushPull."""

    def __init__(self, config_path: Path | str = DEFAULT_CONFIG_PATH) -> None:
        super().__init__()
        self.setWindowTitle("PushPull")
        self.resize(1120, 720)
        self.setMinimumSize(940, 560)

        self.store = ConfigStore(config_path)
        self._repos: list[RepoItem] = []
        self._active_workers = 0
        self._running_workers: dict[str, RepoWorker] = {}
        self._run_steps: dict[str, list[str]] = {}
        self._run_logs: dict[str, list[str]] = {}
        self._batch_promote_paths: list[str] = []
        self._thread_pool = QThreadPool.globalInstance()
        self._thread_pool.setMaxThreadCount(4)

        root = QWidget(self)
        root.setObjectName("MainRoot")
        self.setCentralWidget(root)

        self.main_layout = QVBoxLayout(root)
        self.main_layout.setContentsMargins(20, 18, 20, 18)
        self.main_layout.setSpacing(14)

        self.toolbar = TopToolbar(root)
        self.repo_list = RepoListWidget(root)

        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.repo_list, 1)

        self._connect_signals()
        self.reload_repos()

    def _connect_signals(self) -> None:
        self.toolbar.add_repo_clicked.connect(self.add_repo_dialog)
        self.toolbar.fetch_all_clicked.connect(self.run_fetch_all)
        self.toolbar.run_selected_clicked.connect(self.run_selected)
        self.repo_list.move_up_requested.connect(lambda p: self.move_repo_by_path(p, -1))
        self.repo_list.move_down_requested.connect(lambda p: self.move_repo_by_path(p, 1))
        self.repo_list.remove_requested.connect(self.remove_repo_by_path)

    def reload_repos(self) -> None:
        """Load repositories from repos.json and refresh the UI."""
        self._repos = self.store.load_repos()
        self.repo_list.set_repos(self._repos)
        self.toolbar.set_repo_count(len(self._repos))

    def add_repo_dialog(self) -> None:
        """Prompt the user to select a local Git repository folder."""
        folder = QFileDialog.getExistingDirectory(self, "Git Reposu Seç")
        if not folder:
            return
        self.add_repo_path(folder)

    def add_repo_path(self, folder: str) -> bool:
        """Validate and add a repository folder to repos.json."""
        target = Path(folder)
        if not (target / ".git").exists():
            QMessageBox.warning(
                self,
                "Geçersiz Repo",
                f"Seçilen klasörde '.git' dizini bulunamadı:\n{folder}",
            )
            return False

        self._repos = self.store.add_repo(str(target))
        self.repo_list.set_repos(self._repos)
        self.toolbar.set_repo_count(len(self._repos))
        return True

    def move_repo_by_path(self, repo_path: str, direction: int) -> None:
        """Move a repository row up (-1) or down (+1) and persist order."""
        idx = next((i for i, r in enumerate(self._repos) if r.path == repo_path), -1)
        if idx < 0:
            return
        self._repos = self.store.move_repo(idx, direction)
        self.repo_list.set_repos(self._repos)
        self.toolbar.set_repo_count(len(self._repos))

    def remove_repo_by_path(self, repo_path: str) -> None:
        """Remove a repository row and persist updated list."""
        self._repos = self.store.remove_repo(repo_path)
        self.repo_list.set_repos(self._repos)
        self.toolbar.set_repo_count(len(self._repos))

    def run_fetch_all(self) -> None:
        """Run Fetch + Analyze across all tracked repositories."""
        rows = self.repo_list.iter_rows()
        if not rows or self._active_workers > 0:
            return
        jobs = [(row, PipelineOptions(fetch=True, analyze=True)) for row in rows]
        self._dispatch_jobs(jobs, promote_on_finish=False)

    def run_selected(self) -> None:
        """Run checked pipeline steps for each repository row."""
        if self._active_workers > 0:
            return
        jobs: list[tuple[RepoRowWidget, PipelineOptions]] = []
        for row in self.repo_list.iter_rows():
            opts = row.get_options()
            if opts.selected_steps():
                jobs.append((row, opts))

        if not jobs:
            QMessageBox.information(
                self,
                "Adım Seçilmedi",
                "Çalıştırmak için en az bir repoda bir işlem kutucuğu işaretleyin.",
            )
            return
        self._dispatch_jobs(jobs, promote_on_finish=True)

    def _dispatch_jobs(
        self,
        jobs: list[tuple[RepoRowWidget, PipelineOptions]],
        promote_on_finish: bool,
    ) -> None:
        self._active_workers = len(jobs)
        self._batch_promote_paths = [row.repo_path for row, _ in jobs] if promote_on_finish else []
        self.toolbar.set_busy(True)

        for row, options in jobs:
            row.clear_logs()
            row.set_status(RepoStatus.RUNNING, "Sırada...")
            self._run_steps[row.repo_path] = [s.capitalize() for s in options.selected_steps()]
            self._run_logs[row.repo_path] = []
            worker = RepoWorker(row.repo_path, options)
            worker.setAutoDelete(False)
            self._running_workers[row.repo_path] = worker
            worker.signals.started.connect(self._on_worker_started)
            worker.signals.step_done.connect(self._on_worker_step_done)
            worker.signals.finished.connect(self._on_worker_finished)
            worker.signals.error.connect(self._on_worker_error)
            self._thread_pool.start(worker)

    def _on_worker_started(self, repo_path: str) -> None:
        row = self.repo_list.get_row(repo_path)
        if row is not None:
            row.set_status(RepoStatus.RUNNING, "Çalışıyor...")

    def _on_worker_step_done(self, repo_path: str, result: RepoRunResult) -> None:
        self._run_logs.setdefault(repo_path, []).extend(result.logs)
        row = self.repo_list.get_row(repo_path)
        if row is not None:
            row.append_logs(result.logs)
            row.set_status(result.status, result.message)

    def _on_worker_finished(self, repo_path: str, result: RepoRunResult) -> None:
        self._record_run_history(repo_path, result)
        row = self.repo_list.get_row(repo_path)
        if row is not None:
            row.set_status(result.status, result.message)
            row.clear_all_steps()
        self._mark_worker_done(repo_path)

    def _on_worker_error(self, repo_path: str, result: RepoRunResult) -> None:
        self._run_logs.setdefault(repo_path, []).extend(result.logs)
        self._record_run_history(repo_path, result)
        row = self.repo_list.get_row(repo_path)
        if row is not None:
            row.append_logs(result.logs)
            row.set_status(result.status, result.message)
            row.set_expanded(True)
        self._mark_worker_done(repo_path)

    def _record_run_history(self, repo_path: str, result: RepoRunResult) -> None:
        record = RepoRunRecord(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            steps=self._run_steps.pop(repo_path, [result.step.capitalize()]),
            status=result.status,
            summary=result.message,
            logs=self._run_logs.pop(repo_path, list(result.logs)),
        )
        self._repos = self.store.append_run_record(repo_path, record)
        row = self.repo_list.get_row(repo_path)
        updated = next((r for r in self._repos if r.path == repo_path), None)
        if row is not None and updated is not None:
            row.set_history(updated.history)

    def _mark_worker_done(self, repo_path: str) -> None:
        self._running_workers.pop(repo_path, None)
        self._active_workers = max(0, self._active_workers - 1)
        if self._active_workers == 0:
            self.toolbar.set_busy(False)
            if self._batch_promote_paths:
                self._promote_after_batch()

    def _promote_after_batch(self) -> None:
        """Move recently executed repos to the top while preserving UI row states."""
        snapshots = {
            row.repo_path: (
                row.status_btn.property("status"),
                row.status_btn.text(),
                row.is_expanded(),
                row.get_options(),
            )
            for row in self.repo_list.iter_rows()
        }
        self._repos = self.store.promote_repos_to_top(self._batch_promote_paths)
        self._batch_promote_paths = []
        self.repo_list.set_repos(self._repos)
        for row in self.repo_list.iter_rows():
            snap = snapshots.get(row.repo_path)
            if snap is None:
                continue
            status_val, status_text, expanded, opts = snap
            try:
                status_enum = RepoStatus(status_val)
            except ValueError:
                status_enum = RepoStatus.IDLE
            row.set_status(status_enum, status_text)
            row.set_expanded(expanded)
            for step in opts.selected_steps():
                row.set_step_checked(step, True)
            if opts.commit_message:
                row.set_commit_message(opts.commit_message)


def create_application(
    argv: list[str] | None = None,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> tuple[QApplication, MainWindow]:
    """Create the QApplication and main window instance."""
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("PushPull")
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow(config_path=config_path)
    return app, window


def main() -> int:
    """Launch the PushPull desktop window."""
    app, window = create_application()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
