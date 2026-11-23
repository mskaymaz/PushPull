"""Top action toolbar widget for PushPull."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class TopToolbar(QFrame):
    """Sleek top toolbar with brand header and primary repository actions."""

    add_repo_clicked = Signal()
    fetch_all_clicked = Signal()
    run_selected_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TopToolbar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        self.title_label = QLabel("PushPull", self)
        self.title_label.setObjectName("AppTitle")

        self.count_badge = QLabel("0 repo", self)
        self.count_badge.setObjectName("RepoCountBadge")
        self.count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.add_repo_btn = QPushButton("+ Repo Ekle", self)
        self.add_repo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_repo_btn.clicked.connect(self.add_repo_clicked)

        self.fetch_all_btn = QPushButton("Tümünü Fetch Et", self)
        self.fetch_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fetch_all_btn.clicked.connect(self.fetch_all_clicked)

        self.run_selected_btn = QPushButton("Seçilileri Çalıştır", self)
        self.run_selected_btn.setObjectName("PrimaryButton")
        self.run_selected_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_selected_btn.clicked.connect(self.run_selected_clicked)

        layout.addWidget(self.title_label)
        layout.addWidget(self.count_badge)
        layout.addStretch(1)
        layout.addWidget(self.add_repo_btn)
        layout.addWidget(self.fetch_all_btn)
        layout.addWidget(self.run_selected_btn)

    def set_repo_count(self, count: int) -> None:
        """Update the repository count pill."""
        self.count_badge.setText(f"{count} repo")

    def set_busy(self, busy: bool) -> None:
        """Enable or disable action buttons while workers are running."""
        self.add_repo_btn.setDisabled(busy)
        self.fetch_all_btn.setDisabled(busy)
        self.run_selected_btn.setDisabled(busy)
