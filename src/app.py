"""Application entry point for PushPull."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, QThreadPool, Signal
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
from src.services.gist_sync import pull_sync_payload, push_sync_payload
from src.services.release_service import download_latest_release
from src.services.repo_worker import PipelineOptions, RepoWorker
from src.ui.release_dialog import ReleaseDialog
from src.ui.repo_list import RepoListWidget
from src.ui.repo_row import RepoRowWidget
from src.ui.styles import APP_STYLESHEET
from src.ui.toolbar import TopToolbar


class _GistPullThread(QThread):
    completed = Signal(object, object)

    def __init__(self, gist_id: str | None) -> None:
        super().__init__()
        self.gist_id = gist_id

    def run(self) -> None:
        gid, payload = pull_sync_payload(self.gist_id)
        self.completed.emit(gid, payload)


class _GistPushThread(QThread):
    completed = Signal(bool, object)

    def __init__(self, payload: dict, gist_id: str | None) -> None:
        super().__init__()
        self.payload = payload
        self.gist_id = gist_id

    def run(self) -> None:
        ok, gid = push_sync_payload(self.payload, self.gist_id)
        self.completed.emit(ok, gid)


class _ReleaseDownloadThread(QThread):
    progress = Signal(str, int, int)
    completed = Signal(str, bool, str, str)

    def __init__(self, repo_name: str, repo_path: str, target: str, dest_dir: str) -> None:
        super().__init__()
        self.repo_name = repo_name
        self.repo_path = repo_path
        self.target = target
        self.dest_dir = dest_dir

    def run(self) -> None:
        ok, tag, msg = download_latest_release(
            self.repo_name,
            self.repo_path,
            self.target,
            self.dest_dir,
            progress_cb=lambda done, total: self.progress.emit(self.repo_path, done, total),
        )
        self.completed.emit(self.repo_path, ok, tag, msg)


class MainWindow(QMainWindow):
    """Main application window for PushPull."""

    def __init__(
        self,
        config_path: Path | str = DEFAULT_CONFIG_PATH,
        sync_with_gist: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowTitle("PushPull")
        self.resize(1120, 720)
        self.setMinimumSize(940, 560)

        self.store = ConfigStore(config_path)
        self._sync_with_gist = sync_with_gist
        self._repos: list[RepoItem] = []
        self._active_workers = 0
        self._running_workers: dict[str, RepoWorker] = {}
        self._run_steps: dict[str, list[str]] = {}
        self._run_logs: dict[str, list[str]] = {}
        self._batch_promote_paths: list[str] = []
        self._gist_pull_thread: _GistPullThread | None = None
        self._gist_push_thread: _GistPushThread | None = None
        self._download_threads: dict[str, _ReleaseDownloadThread] = {}
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
        if self._sync_with_gist:
            self._start_gist_pull()

    def _connect_signals(self) -> None:
        self.toolbar.add_repo_clicked.connect(self.add_repo_dialog)
        self.toolbar.map_folder_clicked.connect(self.scan_map_folder_dialog)
        self.toolbar.fetch_all_clicked.connect(self.run_fetch_all)
        self.toolbar.run_selected_clicked.connect(self.run_selected)
        self.repo_list.move_up_requested.connect(lambda p: self.move_repo_by_path(p, -1))
        self.repo_list.move_down_requested.connect(lambda p: self.move_repo_by_path(p, 1))
        self.repo_list.remove_requested.connect(self.remove_repo_by_path)
        self.repo_list.release_requested.connect(self.open_release_dialog)
        self.repo_list.download_requested.connect(self.download_latest_release_dialog)
        self.repo_list.remap_requested.connect(self.remap_repo_dialog)

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
        self._schedule_gist_push()
        return True

    def move_repo_by_path(self, repo_path: str, direction: int) -> None:
        """Move a repository row up (-1) or down (+1) and persist order."""
        idx = next((i for i, r in enumerate(self._repos) if r.path == repo_path), -1)
        if idx < 0:
            return
        self._repos = self.store.move_repo(idx, direction)
        self.repo_list.set_repos(self._repos)
        self.toolbar.set_repo_count(len(self._repos))
        self._schedule_gist_push()

    def remove_repo_by_path(self, repo_path: str) -> None:
        """Remove a repository row and persist updated list."""
        self._repos = self.store.remove_repo(repo_path)
        self.repo_list.set_repos(self._repos)
        self.toolbar.set_repo_count(len(self._repos))
        self._schedule_gist_push()

    def remap_repo_dialog(self, old_path: str) -> None:
        """Prompt user to pick the local folder on this PC for a missing repo."""
        folder = QFileDialog.getExistingDirectory(self, "Bu Bilgisayardaki Repo Klasörünü Seç")
        if not folder:
            return
        if not (Path(folder) / ".git").exists():
            QMessageBox.warning(
                self,
                "Geçersiz Repo",
                f"Seçilen klasörde '.git' dizini bulunamadı:\n{folder}",
            )
            return
        self._repos = self.store.remap_repo_path(old_path, folder)
        self.repo_list.set_repos(self._repos)
        self.toolbar.set_repo_count(len(self._repos))
        self._schedule_gist_push()

    def scan_map_folder_dialog(self) -> None:
        """Scan a parent folder and auto-map local paths for this computer."""
        folder = QFileDialog.getExistingDirectory(self, "Ana Kod Klasörünü Seç")
        if not folder:
            return
        matched, self._repos = self.store.scan_and_map_folder(folder)
        self.repo_list.set_repos(self._repos)
        self.toolbar.set_repo_count(len(self._repos))
        if matched > 0:
            self._schedule_gist_push()
        QMessageBox.information(
            self,
            "Klasör Tarama Tamamlandı",
            f"{matched} repo bu bilgisayardaki klasörüyle eşleştirildi.",
        )

    def open_release_dialog(self, repo_path: str) -> None:
        """Open Release upload dialog and persist chosen target ('self' or 'msklabsapps')."""
        repo = next((r for r in self._repos if r.path == repo_path), None)
        if repo is None:
            return
        dialog = ReleaseDialog(
            repo_name=repo.name,
            repo_path=repo.path,
            saved_target=repo.release_target,
            parent=self,
        )
        if dialog.exec() == ReleaseDialog.DialogCode.Accepted:
            self._repos = self.store.set_release_target(repo.path, dialog.selected_target)
            row = self.repo_list.get_row(repo.path)
            if row is not None:
                row.set_release_target(dialog.selected_target)
                row.append_logs([f"[RELEASE] Yüklendi -> {dialog.release_url}"])
                row.set_status(RepoStatus.SUCCESS, "Release yüklendi")
                row.set_expanded(True)
            self._schedule_gist_push()

    def download_latest_release_dialog(self, repo_path: str) -> None:
        """Download the latest release binary for a repository into a chosen folder."""
        repo = next((r for r in self._repos if r.path == repo_path), None)
        if repo is None or repo.release_target not in ("self", "msklabsapps"):
            return
        if repo_path in self._download_threads and self._download_threads[repo_path].isRunning():
            return

        default_dir = str(Path.home() / "Downloads")
        dest_dir = QFileDialog.getExistingDirectory(
            self,
            f"{repo.name} — İndirme Klasörünü Seç",
            default_dir,
        )
        if not dest_dir:
            return

        row = self.repo_list.get_row(repo_path)
        if row is not None:
            row.set_status(RepoStatus.RUNNING, "İndiriliyor...")

        thread = _ReleaseDownloadThread(repo.name, repo.path, repo.release_target, dest_dir)
        self._download_threads[repo_path] = thread
        thread.progress.connect(self._on_release_download_progress)
        thread.completed.connect(self._on_release_downloaded)
        thread.start()

    def _on_release_download_progress(self, repo_path: str, done: int, total: int) -> None:
        row = self.repo_list.get_row(repo_path)
        if row is None:
            return
        done_mb = done / (1024 * 1024)
        if total > 0:
            pct = min(100, int(done * 100 / total))
            total_mb = total / (1024 * 1024)
            row.set_status(RepoStatus.RUNNING, f"%{pct} ({done_mb:.1f}/{total_mb:.1f} MB)")
        else:
            row.set_status(RepoStatus.RUNNING, f"{done_mb:.1f} MB...")

    def _on_release_downloaded(self, repo_path: str, ok: bool, tag: str, message: str) -> None:
        self._download_threads.pop(repo_path, None)
        row = self.repo_list.get_row(repo_path)
        if row is None:
            return
        if ok:
            row.set_status(RepoStatus.SUCCESS, f"İndirildi: {tag}")
            row.append_logs([f"[DOWNLOAD] {message}"])
        else:
            row.set_status(RepoStatus.ERROR, "İndirme hatası")
            row.append_logs([f"[DOWNLOAD HATA] {message}"])
            row.set_expanded(True)

    def _start_gist_pull(self) -> None:
        self.toolbar.set_sync_status("Gist senkronize ediliyor...")
        self._gist_pull_thread = _GistPullThread(self.store.load_gist_id())
        self._gist_pull_thread.completed.connect(self._on_gist_pulled)
        self._gist_pull_thread.start()

    def _on_gist_pulled(self, gist_id: str | None, payload: dict | None) -> None:
        if gist_id:
            self.store.save_gist_id(gist_id)
        if payload and payload.get("repos"):
            self._repos = self.store.merge_remote_payload(payload)
            self.repo_list.set_repos(self._repos)
            self.toolbar.set_repo_count(len(self._repos))
            self.toolbar.set_sync_status("Gist: Güncel")
            return
        if self._repos:
            self._schedule_gist_push()
        else:
            self.toolbar.set_sync_status("Gist: Hazır")

    def _schedule_gist_push(self) -> None:
        if not self._sync_with_gist:
            return
        if self._gist_push_thread is not None and self._gist_push_thread.isRunning():
            return
        self.toolbar.set_sync_status("Gist güncelleniyor...")
        self._gist_push_thread = _GistPushThread(
            self.store.export_sync_payload(),
            self.store.load_gist_id(),
        )
        self._gist_push_thread.completed.connect(self._on_gist_pushed)
        self._gist_push_thread.start()

    def _on_gist_pushed(self, ok: bool, gist_id: str | None) -> None:
        if ok and gist_id:
            self.store.save_gist_id(gist_id)
            self.toolbar.set_sync_status("Gist: Güncel")
        else:
            self.toolbar.set_sync_status("Gist: Çevrimdışı")

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
        self._schedule_gist_push()


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
