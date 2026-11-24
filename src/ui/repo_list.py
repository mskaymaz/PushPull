"""Scrollable repository table container with aligned column headers."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.models.repo_models import RepoItem
from src.ui.repo_row import (
    CHECKBOX_COL_WIDTH,
    DELETE_COL_WIDTH,
    RELEASE_COL_WIDTH,
    STATUS_COL_WIDTH,
    RepoRowWidget,
)

HEADER_STEPS = ("Fetch", "Analyze", "Stash", "Pull", "Commit", "Push")


class TableHeader(QFrame):
    """Column header bar aligned with RepoRowWidget columns."""

    column_toggle_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TableHeader")
        self._step_buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Spacer matching up/down buttons (24 + 24 + 6)
        controls_spacer = QWidget(self)
        controls_spacer.setFixedWidth(54)
        layout.addWidget(controls_spacer)

        repo_label = QLabel("REPO", self)
        repo_label.setObjectName("HeaderLabel")
        repo_label.setMinimumWidth(200)
        layout.addWidget(repo_label, 1)

        for title in HEADER_STEPS:
            step_key = title.lower()
            btn = QPushButton(title.upper(), self)
            btn.setObjectName("HeaderStepButton")
            btn.setFixedWidth(CHECKBOX_COL_WIDTH)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"Tüm satırlarda '{title}' seç / kaldır")
            btn.clicked.connect(
                lambda _checked=False, s=step_key: self.column_toggle_requested.emit(s)
            )
            self._step_buttons[step_key] = btn
            layout.addWidget(btn)

        status_label = QLabel("DURUM", self)
        status_label.setObjectName("HeaderLabel")
        status_label.setFixedWidth(STATUS_COL_WIDTH)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)

        release_label = QLabel("RELEASE", self)
        release_label.setObjectName("HeaderLabel")
        release_label.setFixedWidth(RELEASE_COL_WIDTH)
        release_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(release_label)

        delete_spacer = QWidget(self)
        delete_spacer.setFixedWidth(DELETE_COL_WIDTH)
        layout.addWidget(delete_spacer)


class RepoListWidget(QWidget):
    """Vertically scrollable repository list with header and empty state."""

    move_up_requested = Signal(str)
    move_down_requested = Signal(str)
    remove_requested = Signal(str)
    release_requested = Signal(str)
    remap_requested = Signal(str)
    commit_toggled = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[RepoRowWidget] = []
        self._rows_by_path: dict[str, RepoRowWidget] = {}

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        self.header = TableHeader(self)
        self.header.column_toggle_requested.connect(self.toggle_column)
        root_layout.addWidget(self.header)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("RepoScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget(self.scroll_area)
        self.content_widget.setObjectName("RepoScrollContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.content_layout.setSpacing(8)

        self.empty_label = QLabel(
            "Henüz takip edilen repo yok. Başlamak için '+ Repo Ekle' butonunu kullanın.",
            self.content_widget,
        )
        self.empty_label.setObjectName("EmptyStateLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.empty_label)
        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area, 1)

    def set_repos(self, repos: list[RepoItem]) -> None:
        """Rebuild row widgets from the ordered repository list."""
        for row in self._rows:
            self.content_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self._rows_by_path.clear()

        self.empty_label.setVisible(len(repos) == 0)

        total = len(repos)
        for idx, repo in enumerate(repos):
            row = RepoRowWidget(repo, self.content_widget)
            row.set_move_bounds(is_first=(idx == 0), is_last=(idx == total - 1))
            row.move_up_requested.connect(self.move_up_requested)
            row.move_down_requested.connect(self.move_down_requested)
            row.remove_requested.connect(self.remove_requested)
            row.release_requested.connect(self.release_requested)
            row.remap_requested.connect(self.remap_requested)
            row.commit_toggled.connect(self.commit_toggled)

            # Insert before empty_label and bottom stretch
            self.content_layout.insertWidget(idx, row)
            self._rows.append(row)
            self._rows_by_path[repo.path] = row

    def get_row(self, repo_path: str) -> RepoRowWidget | None:
        """Return the RepoRowWidget for a given repository path."""
        return self._rows_by_path.get(repo_path)

    def iter_rows(self) -> list[RepoRowWidget]:
        """Return all current RepoRowWidget instances in display order."""
        return list(self._rows)

    def toggle_column(self, step: str) -> None:
        """Select all rows for a step column, or unselect all if already all checked."""
        if not self._rows:
            return
        all_checked = all(row.is_step_checked(step) for row in self._rows)
        target_state = not all_checked
        for row in self._rows:
            row.set_step_checked(step, target_state)
