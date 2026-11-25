"""Modal dialog for uploading compiled binaries to GitHub Releases."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from src.services.release_service import (
    PUBLIC_RELEASE_REPO,
    detect_repo_slug,
    suggest_artifact,
    suggest_tag,
    upload_release,
)


class _ReleaseUploadThread(QThread):
    completed = Signal(bool, str)

    def __init__(
        self,
        target_repo: str,
        tag: str,
        file_path: str,
        notes: str,
        repo_name: str = "",
    ) -> None:
        super().__init__()
        self.target_repo = target_repo
        self.tag = tag
        self.file_path = file_path
        self.notes = notes
        self.repo_name = repo_name

    def run(self) -> None:
        ok, msg = upload_release(
            target_repo=self.target_repo,
            tag=self.tag,
            file_path=self.file_path,
            notes=self.notes,
            repo_name=self.repo_name,
        )
        self.completed.emit(ok, msg)


class ReleaseDialog(QDialog):
    """Dialog to configure target repo (Private/Self vs Public/MSKLabsApps) and upload."""

    def __init__(
        self,
        repo_name: str,
        repo_path: str,
        saved_target: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Release Yükle — {repo_name}")
        self.setMinimumWidth(520)
        self.repo_name = repo_name
        self.repo_path = repo_path
        self.own_slug = detect_repo_slug(repo_path) or ""
        self.selected_target = saved_target if saved_target in ("self", "msklabsapps") else "self"
        self.release_url = ""
        self._worker: _ReleaseUploadThread | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        header = QLabel(f"<b>{repo_name}</b> — Derlenmiş Dosyayı GitHub Releases'a Yükle", self)
        layout.addWidget(header)

        # Target radio group
        target_label = QLabel("Yayın Hedefi (repos.json içinde kalıcı kaydedilir):", self)
        layout.addWidget(target_label)

        own_display = self.own_slug or "Origin bulunamadı"
        self.radio_self = QRadioButton(f"Kendi Reposu — Özel / Bireysel ({own_display})", self)
        self.radio_public = QRadioButton(
            f"MSKLabsApps — Public Dağıtım ({PUBLIC_RELEASE_REPO})", self
        )

        self.target_group = QButtonGroup(self)
        self.target_group.addButton(self.radio_self)
        self.target_group.addButton(self.radio_public)

        if self.selected_target == "msklabsapps":
            self.radio_public.setChecked(True)
        else:
            self.radio_self.setChecked(True)

        self.radio_self.toggled.connect(self._on_target_changed)
        layout.addWidget(self.radio_self)
        layout.addWidget(self.radio_public)

        # File chooser
        layout.addWidget(QLabel("Yüklenecek Dosya (.exe / .apk / .zip):", self))
        file_row = QHBoxLayout()
        self.file_input = QLineEdit(suggest_artifact(repo_path), self)
        self.browse_btn = QPushButton("Gözat...", self)
        self.browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self.file_input, 1)
        file_row.addWidget(self.browse_btn)
        layout.addLayout(file_row)

        # Tag
        layout.addWidget(QLabel("Release Tag:", self))
        self.tag_input = QLineEdit(suggest_tag(repo_name, self.selected_target), self)
        layout.addWidget(self.tag_input)

        # Notes
        layout.addWidget(QLabel("Notlar (opsiyonel):", self))
        self.notes_input = QLineEdit(self)
        self.notes_input.setPlaceholderText("Örn: İlk kararlı sürüm")
        layout.addWidget(self.notes_input)

        # Status + Actions
        self.status_label = QLabel("", self)
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.cancel_btn = QPushButton("İptal", self)
        self.cancel_btn.clicked.connect(self.reject)
        self.upload_btn = QPushButton("Release Yükle", self)
        self.upload_btn.setObjectName("PrimaryButton")
        self.upload_btn.clicked.connect(self._start_upload)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.upload_btn)
        layout.addLayout(btn_row)

    def _on_target_changed(self) -> None:
        self.selected_target = "self" if self.radio_self.isChecked() else "msklabsapps"
        self.tag_input.setText(suggest_tag(self.repo_name, self.selected_target))

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Release Dosyası Seç",
            self.repo_path,
            "Uygulama / Arşiv (*.exe *.apk *.zip *.msi);;Tüm Dosyalar (*.*)",
        )
        if path:
            self.file_input.setText(path)

    def _start_upload(self) -> None:
        target_repo = self.own_slug if self.selected_target == "self" else PUBLIC_RELEASE_REPO
        if not target_repo:
            QMessageBox.warning(
                self,
                "Remote Bulunamadı",
                "Bu repoda GitHub 'origin' remote adresi tanımlı değil.",
            )
            return

        file_path = self.file_input.text().strip()
        tag = self.tag_input.text().strip()
        if not file_path or not tag:
            QMessageBox.warning(self, "Eksik Bilgi", "Dosya ve Release Tag alanları zorunludur.")
            return

        self.upload_btn.setDisabled(True)
        self.cancel_btn.setDisabled(True)
        self.status_label.setText(f"Yükleniyor ({target_repo} -> {tag})...")

        self._worker = _ReleaseUploadThread(
            target_repo=target_repo,
            tag=tag,
            file_path=file_path,
            notes=self.notes_input.text(),
            repo_name=self.repo_name,
        )
        self._worker.completed.connect(self._on_upload_finished)
        self._worker.start()

    def _on_upload_finished(self, ok: bool, message: str) -> None:
        self.upload_btn.setDisabled(False)
        self.cancel_btn.setDisabled(False)
        if ok:
            self.release_url = message
            self.accept()
            return

        self.status_label.setText("")
        QMessageBox.critical(self, "Release Hatası", message)
