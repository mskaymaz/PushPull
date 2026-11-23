"""Single repository row widget with checkboxes, status pill, and accordion log drawer."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.repo_models import RepoItem, RepoStatus
from src.services.repo_worker import PipelineOptions

STEP_KEYS = ("fetch", "analyze", "stash", "pull", "commit", "push")
CHECKBOX_COL_WIDTH = 62
STATUS_COL_WIDTH = 176
DELETE_COL_WIDTH = 30

STATUS_DEFAULT_TEXT = {
    RepoStatus.IDLE: "Hazır",
    RepoStatus.RUNNING: "Çalışıyor...",
    RepoStatus.SUCCESS: "Tamam",
    RepoStatus.WARNING: "Uyarı",
    RepoStatus.ERROR: "Hata",
}


class RepoRowWidget(QFrame):
    """Compact repository row card with an inline expandable accordion log drawer."""

    move_up_requested = Signal(str)
    move_down_requested = Signal(str)
    remove_requested = Signal(str)
    commit_toggled = Signal(str, bool)

    def __init__(self, repo: RepoItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RepoRowCard")
        self.repo_path = repo.path
        self.repo_name = repo.name
        self._expanded = False
        self._commit_message = ""
        self._checkboxes: dict[str, QCheckBox] = {}

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top row bar
        row_widget = QWidget(self)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(12, 9, 12, 9)
        row_layout.setSpacing(6)

        # Move up / down controls
        self.up_btn = QPushButton("▲", row_widget)
        self.up_btn.setObjectName("RowIconButton")
        self.up_btn.setFixedSize(24, 24)
        self.up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.up_btn.setToolTip("Yukarı taşı")
        self.up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.repo_path))

        self.down_btn = QPushButton("▼", row_widget)
        self.down_btn.setObjectName("RowIconButton")
        self.down_btn.setFixedSize(24, 24)
        self.down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_btn.setToolTip("Aşağı taşı")
        self.down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.repo_path))

        row_layout.addWidget(self.up_btn)
        row_layout.addWidget(self.down_btn)

        # Repo name & path
        info_widget = QWidget(row_widget)
        info_widget.setMinimumWidth(200)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(4, 0, 8, 0)
        info_layout.setSpacing(1)

        self.name_label = QLabel(repo.name, info_widget)
        self.name_label.setObjectName("RepoNameLabel")
        self.path_label = QLabel(repo.path, info_widget)
        self.path_label.setObjectName("RepoPathLabel")
        self.path_label.setToolTip(repo.path)

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.path_label)
        row_layout.addWidget(info_widget, 1)

        # 6 Step checkboxes
        for step in STEP_KEYS:
            cell = QWidget(row_widget)
            cell.setFixedWidth(CHECKBOX_COL_WIDTH)
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cb = QCheckBox(cell)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            if step == "commit":
                cb.toggled.connect(self._on_commit_checkbox_toggled)
            self._checkboxes[step] = cb
            cell_layout.addWidget(cb)
            row_layout.addWidget(cell)

        # Status pill badge (click toggles accordion)
        self.status_btn = QPushButton(STATUS_DEFAULT_TEXT[repo.status], row_widget)
        self.status_btn.setObjectName("StatusBadge")
        self.status_btn.setFixedWidth(STATUS_COL_WIDTH)
        self.status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_btn.setToolTip("Log detayını aç / kapat")
        self.status_btn.clicked.connect(self.toggle_expanded)
        self._apply_status_style(repo.status)
        row_layout.addWidget(self.status_btn)

        # Delete button
        self.delete_btn = QPushButton("✕", row_widget)
        self.delete_btn.setObjectName("RowDeleteButton")
        self.delete_btn.setFixedSize(DELETE_COL_WIDTH, 26)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setToolTip("Listeden kaldır")
        self.delete_btn.clicked.connect(lambda: self.remove_requested.emit(self.repo_path))
        row_layout.addWidget(self.delete_btn)

        root_layout.addWidget(row_widget)

        # Inline commit message bar (visible when Commit is checked)
        self.commit_bar = QFrame(self)
        self.commit_bar.setObjectName("CommitBar")
        self.commit_bar.setVisible(False)
        commit_layout = QHBoxLayout(self.commit_bar)
        commit_layout.setContentsMargins(14, 7, 14, 7)
        commit_layout.setSpacing(10)

        commit_hint = QLabel("Commit Mesajı:", self.commit_bar)
        commit_hint.setObjectName("CommitHintLabel")

        self.commit_input = QLineEdit(self.commit_bar)
        self.commit_input.setObjectName("CommitInput")
        self.commit_input.setPlaceholderText(
            "Boş bırakılırsa otomatik üretilir: Auto-commit: YYYY-AA-GG SS:DD"
        )
        self.commit_input.textChanged.connect(self.set_commit_message)

        commit_layout.addWidget(commit_hint)
        commit_layout.addWidget(self.commit_input, 1)
        root_layout.addWidget(self.commit_bar)

        # Inline accordion log drawer
        self.drawer = QFrame(self)
        self.drawer.setObjectName("AccordionDrawer")
        self.drawer.setVisible(False)
        drawer_layout = QVBoxLayout(self.drawer)
        drawer_layout.setContentsMargins(14, 10, 14, 10)
        drawer_layout.setSpacing(6)

        self.log_output = QPlainTextEdit(self.drawer)
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(135)
        self.log_output.setPlaceholderText("Bu repo için henüz işlem çıktısı yok.")
        if repo.logs:
            self.log_output.setPlainText("\n".join(repo.logs))

        drawer_layout.addWidget(self.log_output)
        root_layout.addWidget(self.drawer)

    def set_move_bounds(self, is_first: bool, is_last: bool) -> None:
        """Enable or disable up/down buttons based on row position."""
        self.up_btn.setDisabled(is_first)
        self.down_btn.setDisabled(is_last)

    def set_status(self, status: RepoStatus, text: str | None = None) -> None:
        """Update status pill text and visual state."""
        self.status_btn.setText(text or STATUS_DEFAULT_TEXT[status])
        self._apply_status_style(status)

    def _apply_status_style(self, status: RepoStatus) -> None:
        self.status_btn.setProperty("status", status.value)
        self.status_btn.style().unpolish(self.status_btn)
        self.status_btn.style().polish(self.status_btn)

    def set_expanded(self, expanded: bool) -> None:
        """Expand or collapse the inline accordion log drawer."""
        self._expanded = expanded
        self.drawer.setVisible(expanded)

    def toggle_expanded(self) -> None:
        """Toggle the inline accordion log drawer."""
        self.set_expanded(not self._expanded)

    def is_expanded(self) -> bool:
        """Return whether the accordion log drawer is currently open."""
        return self._expanded

    def append_logs(self, lines: list[str]) -> None:
        """Append log lines to the accordion output view."""
        if not lines:
            return
        self.log_output.appendPlainText("\n".join(lines))

    def clear_logs(self) -> None:
        """Clear the accordion output view."""
        self.log_output.clear()

    def _on_commit_checkbox_toggled(self, checked: bool) -> None:
        self.commit_bar.setVisible(checked)
        if checked:
            self.commit_input.setFocus()
        self.commit_toggled.emit(self.repo_path, checked)

    def set_commit_message(self, message: str) -> None:
        """Store the commit message associated with this row."""
        self._commit_message = message
        if self.commit_input.text() != message:
            self.commit_input.setText(message)

    def set_step_checked(self, step: str, checked: bool) -> None:
        """Programmatically check or uncheck a step checkbox."""
        if step in self._checkboxes:
            self._checkboxes[step].setChecked(checked)

    def is_step_checked(self, step: str) -> bool:
        """Return whether a step checkbox is currently checked."""
        cb = self._checkboxes.get(step)
        return cb.isChecked() if cb is not None else False

    def clear_all_steps(self) -> None:
        """Uncheck all step checkboxes and clear any pending commit message."""
        for cb in self._checkboxes.values():
            cb.setChecked(False)
        self.set_commit_message("")

    def get_options(self) -> PipelineOptions:
        """Return currently selected PipelineOptions for this row."""
        return PipelineOptions(
            fetch=self._checkboxes["fetch"].isChecked(),
            analyze=self._checkboxes["analyze"].isChecked(),
            stash=self._checkboxes["stash"].isChecked(),
            pull=self._checkboxes["pull"].isChecked(),
            commit=self._checkboxes["commit"].isChecked(),
            push=self._checkboxes["push"].isChecked(),
            commit_message=self._commit_message,
        )
