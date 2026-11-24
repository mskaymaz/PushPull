"""Centralized design tokens and Qt stylesheet for PushPull (light, airy theme)."""

from __future__ import annotations

APP_STYLESHEET = """
QMainWindow, QWidget#MainRoot, QDialog {
    background-color: #F3F6FB;
    color: #1E293B;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QDialog QLineEdit {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 7px;
    padding: 6px 10px;
}

QDialog QLineEdit:focus {
    border-color: #2563EB;
}

QFrame#TopToolbar {
    background-color: #FFFFFF;
    border: 1px solid #DCE3EE;
    border-radius: 12px;
}

QLabel#AppTitle {
    color: #0F172A;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.2px;
}

QLabel#RepoCountBadge {
    background-color: #EFF4FC;
    color: #475569;
    border: 1px solid #D8E2F0;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton {
    background-color: #F8FAFC;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12.5px;
}

QPushButton:hover {
    background-color: #EFF4FB;
    border-color: #94A3B8;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

QPushButton:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}

QPushButton#PrimaryButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #2563EB;
}

QPushButton#PrimaryButton:hover {
    background-color: #1D4ED8;
    border-color: #1D4ED8;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1E40AF;
}

QPushButton#PrimaryButton:disabled {
    background-color: #BFDBFE;
    color: #EFF6FF;
    border-color: #BFDBFE;
}

/* Table Header & Scrollable Container */
QFrame#TableHeader {
    background-color: #EBF0F7;
    border: 1px solid #DCE3EE;
    border-radius: 10px;
}

QLabel#HeaderLabel {
    color: #475569;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
}

QPushButton#HeaderStepButton {
    background-color: transparent;
    color: #475569;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px 2px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
}

QPushButton#HeaderStepButton:hover {
    background-color: #DCE5F2;
    color: #0F172A;
    border-color: #CBD5E1;
}

QPushButton#HeaderStepButton:pressed {
    background-color: #CBD5E1;
}

QScrollArea#RepoScrollArea {
    background: transparent;
    border: none;
}

QWidget#RepoScrollContent {
    background: transparent;
}

QLabel#EmptyStateLabel {
    color: #64748B;
    font-size: 13.5px;
    padding: 36px;
    background-color: #FFFFFF;
    border: 1px dashed #CBD5E1;
    border-radius: 12px;
}

/* Repo Row Card */
QFrame#RepoRowCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}

QFrame#RepoRowCard:hover {
    border-color: #93C5FD;
    background-color: #FAFCFF;
}

QLabel#RepoNameLabel {
    color: #0F172A;
    font-size: 13.5px;
    font-weight: 600;
}

QLabel#RepoPathLabel {
    color: #64748B;
    font-size: 11px;
}

/* Row Micro Action Buttons */
QPushButton#RowIconButton {
    background-color: transparent;
    color: #64748B;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
    font-size: 11px;
    font-weight: 700;
}

QPushButton#RowIconButton:hover {
    background-color: #E2E8F0;
    color: #0F172A;
    border-color: #CBD5E1;
}

QPushButton#RowIconButton:disabled {
    color: #CBD5E1;
    background-color: transparent;
    border-color: transparent;
}

QPushButton#RowDeleteButton {
    background-color: transparent;
    color: #94A3B8;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#RowDeleteButton:hover {
    background-color: #FEE2E2;
    color: #DC2626;
    border-color: #FCA5A5;
}

/* Release Target Pill Button */
QPushButton#ReleaseButton {
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 11.5px;
    font-weight: 700;
}

QPushButton#ReleaseButton[rel_target="none"] {
    background-color: #F1F5F9;
    color: #64748B;
    border: 1px solid #CBD5E1;
}

QPushButton#ReleaseButton[rel_target="none"]:hover {
    background-color: #E2E8F0;
    color: #334155;
}

QPushButton#ReleaseButton[rel_target="self"] {
    background-color: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #FCA5A5;
}

QPushButton#ReleaseButton[rel_target="self"]:hover {
    background-color: #FECACA;
}

QPushButton#ReleaseButton[rel_target="msklabsapps"] {
    background-color: #DCFCE7;
    color: #15803D;
    border: 1px solid #86EFAC;
}

QPushButton#ReleaseButton[rel_target="msklabsapps"]:hover {
    background-color: #BBF7D0;
}

/* Custom Checkbox */
QCheckBox {
    spacing: 0px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1.5px solid #94A3B8;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #2563EB;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #2563EB;
}

QCheckBox::indicator:disabled {
    background-color: #F1F5F9;
    border-color: #CBD5E1;
}

/* Status Pill Badge */
QPushButton#StatusBadge {
    border-radius: 11px;
    padding: 4px 10px;
    font-size: 11.5px;
    font-weight: 600;
    text-align: center;
}

QPushButton#StatusBadge[status="idle"] {
    background-color: #F1F5F9;
    color: #475569;
    border: 1px solid #CBD5E1;
}

QPushButton#StatusBadge[status="running"] {
    background-color: #DBEAFE;
    color: #1D4ED8;
    border: 1px solid #93C5FD;
}

QPushButton#StatusBadge[status="success"] {
    background-color: #DCFCE7;
    color: #15803D;
    border: 1px solid #86EFAC;
}

QPushButton#StatusBadge[status="warning"] {
    background-color: #FEF3C7;
    color: #B45309;
    border: 1px solid #FCD34D;
}

QPushButton#StatusBadge[status="error"] {
    background-color: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #FCA5A5;
}

/* Commit Inline Bar */
QFrame#CommitBar {
    background-color: #F8FAFC;
    border-top: 1px solid #E2E8F0;
}

QLabel#CommitHintLabel {
    color: #475569;
    font-size: 11.5px;
    font-weight: 600;
}

QLineEdit#CommitInput {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 12px;
}

QLineEdit#CommitInput:focus {
    border-color: #2563EB;
    background-color: #FFFFFF;
}

/* Accordion Log Drawer */
QFrame#AccordionDrawer {
    background-color: #F8FAFC;
    border-top: 1px solid #E2E8F0;
    border-bottom-left-radius: 9px;
    border-bottom-right-radius: 9px;
}

QLabel#HistorySectionLabel {
    color: #64748B;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.4px;
}

QListWidget#HistoryList {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 7px;
    padding: 3px;
    color: #334155;
    font-size: 12px;
    outline: none;
}

QListWidget#HistoryList::item {
    padding: 5px 8px;
    border-radius: 5px;
}

QListWidget#HistoryList::item:hover {
    background-color: #EFF4FB;
}

QListWidget#HistoryList::item:selected {
    background-color: #DBEAFE;
    color: #1E3A8A;
    font-weight: 600;
}

QPlainTextEdit#LogOutput {
    background-color: transparent;
    color: #334155;
    border: none;
    font-family: "Cascadia Mono", "Consolas", "Courier New", monospace;
    font-size: 11.5px;
    selection-background-color: #BFDBFE;
}

/* Scrollbar */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 0;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
