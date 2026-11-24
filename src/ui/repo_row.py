"""Single repository row widget with checkboxes, status pill, and accordion log drawer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.repo_models import RepoItem, RepoRunRecord, RepoStatus
from src.services.repo_worker import PipelineOptions

STEP_KEYS = ("fetch", "analyze", "stash", "pull", "commit", "push")
CHECKBOX_COL_WIDTH = 62
STATUS_COL_WIDTH = 146
RELEASE_COL_WIDTH = 86
DOWNLOAD_COL_WIDTH = 30
DELETE_COL_WIDTH = 30

STATUS_DEFAULT_TEXT = {
    RepoStatus.IDLE: "Hazır",
    RepoStatus.RUNNING: "Çalışıyor...",
    RepoStatus.SUCCESS: "Tamam",
    RepoStatus.WARNING: "Uyarı",
    RepoStatus.ERROR: "Hata",
}


def _make_download_icon() -> QIcon:
    """Create a crisp vector download tray-and-arrow icon for light theme."""
    icon = QIcon()
    for mode, color_hex in (
        (QIcon.Mode.Normal, "#2563EB"),
        (QIcon.Mode.Disabled, "#CBD5E1"),
    ):
        pix = QPixmap(16, 16)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color_hex), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        # Vertical shaft
        painter.drawLine(8, 2, 8, 10)
        # Arrow head
        painter.drawLine(5, 7, 8, 10)
        painter.drawLine(11, 7, 8, 10)
        # Bottom tray
        painter.drawLine(3, 12, 3, 14)
        painter.drawLine(3, 14, 13, 14)
        painter.drawLine(13, 14, 13, 12)
        painter.end()
        icon.addPixmap(pix, mode)
    return icon


class RepoRowWidget(QFrame):
    """Compact repository row card with an inline expandable accordion log drawer."""

    move_up_requested = Signal(str)
    move_down_requested = Signal(str)
    remove_requested = Signal(str)
    release_requested = Signal(str)
    download_requested = Signal(str)
    remap_requested = Signal(str)
    commit_toggled = Signal(str, bool)

    def __init__(self, repo: RepoItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RepoRowCard")
        self.repo_path = repo.path
        self.repo_name = repo.name
        self._expanded = False
        self._commit_message = ""
        self._checkboxes: dict[str, QCheckBox] = {}
        self._history: list[RepoRunRecord] = []

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
        self._path_missing = not (repo.path and Path(repo.path).exists())
        path_text = (
            "⚠ Bu bilgisayarda klasör bulunamadı — Konum Seç"
            if self._path_missing
            else repo.path
        )
        self.path_label = QLabel(path_text, info_widget)
        self.path_label.setObjectName("RepoPathLabel")
        self.path_label.setToolTip(repo.path or "Konum atanmamış")

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
            elif step in ("pull", "push"):
                cb.toggled.connect(
                    lambda checked, s=step: self._on_dependent_step_toggled(s, checked)
                )
            self._checkboxes[step] = cb
            cell_layout.addWidget(cb)
            row_layout.addWidget(cell)

        # Status pill badge (click toggles accordion, or remaps if path missing)
        initial_status = RepoStatus.WARNING if self._path_missing else repo.status
        initial_text = "⚠ Konum Seç" if self._path_missing else STATUS_DEFAULT_TEXT[repo.status]
        self.status_btn = QPushButton(initial_text, row_widget)
        self.status_btn.setObjectName("StatusBadge")
        self.status_btn.setFixedWidth(STATUS_COL_WIDTH)
        self.status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_btn.setToolTip(
            "Bu bilgisayardaki repo klasörünü seç"
            if self._path_missing
            else "Log detayını aç / kapat"
        )
        self.status_btn.clicked.connect(self._on_status_clicked)
        self._apply_status_style(initial_status)
        row_layout.addWidget(self.status_btn)

        # Release upload button (color-coded by target: none/self/msklabsapps)
        self.release_btn = QPushButton("Rel", row_widget)
        self.release_btn.setObjectName("ReleaseButton")
        self.release_btn.setFixedWidth(RELEASE_COL_WIDTH)
        self.release_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.release_btn.setToolTip("GitHub Releases'a derlenmiş dosya yükle")
        self.release_btn.clicked.connect(lambda: self.release_requested.emit(self.repo_path))
        row_layout.addWidget(self.release_btn)

        # Latest release download button
        self.download_btn = QPushButton("", row_widget)
        self.download_btn.setObjectName("RowIconButton")
        self.download_btn.setIcon(_make_download_icon())
        self.download_btn.setIconSize(QSize(15, 15))
        self.download_btn.setFixedSize(DOWNLOAD_COL_WIDTH, 26)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(lambda: self.download_requested.emit(self.repo_path))
        row_layout.addWidget(self.download_btn)

        self.set_release_target(repo.release_target)

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
            "Opsiyonel not ekleyin (commit anında sonuna otomatik yy.aa.gg_ss.dd eklenir)"
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

        history_label = QLabel("SON 5 İŞLEM", self.drawer)
        history_label.setObjectName("HistorySectionLabel")
        drawer_layout.addWidget(history_label)

        self.history_list = QListWidget(self.drawer)
        self.history_list.setObjectName("HistoryList")
        self.history_list.setFixedHeight(112)
        self.history_list.currentRowChanged.connect(self._on_history_selected)
        drawer_layout.addWidget(self.history_list)

        self.log_output = QPlainTextEdit(self.drawer)
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(125)
        self.log_output.setPlaceholderText("Bu repo için henüz işlem çıktısı yok.")

        drawer_layout.addWidget(self.log_output)
        root_layout.addWidget(self.drawer)

        self.set_history(repo.history)
        if repo.logs and not repo.history:
            self.log_output.setPlainText("\n".join(repo.logs))

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

    def set_release_target(self, target: str) -> None:
        """Update Release button label, color, and download availability."""
        if target == "self":
            self.release_btn.setText("Rel: Özel")
            prop = "self"
            self.download_btn.setEnabled(True)
            self.download_btn.setToolTip("Son sürümü kendi Releases'ından indir")
        elif target == "msklabsapps":
            self.release_btn.setText("Rel: Public")
            prop = "msklabsapps"
            self.download_btn.setEnabled(True)
            self.download_btn.setToolTip("Son sürümü MSKLabsApps Releases'tan indir")
        else:
            self.release_btn.setText("Rel")
            prop = "none"
            self.download_btn.setEnabled(False)
            self.download_btn.setToolTip("İndirmek için önce Release hedefi seçin")
        self.release_btn.setProperty("rel_target", prop)
        self.release_btn.style().unpolish(self.release_btn)
        self.release_btn.style().polish(self.release_btn)

    def _on_status_clicked(self) -> None:
        if self._path_missing:
            self.remap_requested.emit(self.repo_path)
            return
        self.toggle_expanded()

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
        """Clear the accordion output view for a new live run."""
        self.history_list.clearSelection()
        self.log_output.clear()

    def set_history(self, history: list[RepoRunRecord]) -> None:
        """Populate the last-5 run history list and display the newest entry."""
        self._history = list(history)
        self.history_list.blockSignals(True)
        self.history_list.clear()

        if not self._history:
            placeholder = QListWidgetItem("Henüz kayıtlı işlem yok.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.history_list.addItem(placeholder)
            self.history_list.blockSignals(False)
            return

        status_icons = {
            RepoStatus.SUCCESS: "● Tamam",
            RepoStatus.WARNING: "▲ Uyarı",
            RepoStatus.ERROR: "✕ Hata",
            RepoStatus.IDLE: "• Hazır",
            RepoStatus.RUNNING: "… Çalışıyor",
        }
        for rec in self._history:
            steps_txt = ", ".join(rec.steps) if rec.steps else "-"
            badge = status_icons.get(rec.status, rec.status.value)
            label = f"{rec.timestamp}  |  {steps_txt}  |  {badge}  —  {rec.summary}"
            self.history_list.addItem(QListWidgetItem(label))

        self.history_list.blockSignals(False)
        self.history_list.setCurrentRow(0)
        self._on_history_selected(0)

    def _on_history_selected(self, index: int) -> None:
        if 0 <= index < len(self._history):
            self.log_output.setPlainText("\n".join(self._history[index].logs))

    def _on_commit_checkbox_toggled(self, checked: bool) -> None:
        self.commit_bar.setVisible(checked)
        if checked:
            self.commit_input.setFocus()
        self.commit_toggled.emit(self.repo_path, checked)

    def _on_dependent_step_toggled(self, step: str, checked: bool) -> None:
        """Auto-check prerequisite steps when Pull or Push is selected."""
        if not checked:
            return
        prerequisites = ("fetch", "analyze") if step == "pull" else ("fetch", "analyze", "commit")
        for req in prerequisites:
            if not self.is_step_checked(req):
                self.set_step_checked(req, True)

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
