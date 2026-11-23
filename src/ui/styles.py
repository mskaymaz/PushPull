"""Centralized design tokens and Qt stylesheet for PushPull."""

from __future__ import annotations

APP_STYLESHEET = """
QMainWindow, QWidget#MainRoot {
    background-color: #0B1017;
    color: #E6EDF3;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QFrame#TopToolbar {
    background-color: #121923;
    border: 1px solid #233044;
    border-radius: 12px;
}

QLabel#AppTitle {
    color: #F0F6FC;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.2px;
}

QLabel#RepoCountBadge {
    background-color: #1B2534;
    color: #8B98AB;
    border: 1px solid #263449;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton {
    background-color: #1A2332;
    color: #E6EDF3;
    border: 1px solid #2B394F;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12.5px;
}

QPushButton:hover {
    background-color: #222E42;
    border-color: #3A4D6B;
}

QPushButton:pressed {
    background-color: #151D29;
}

QPushButton:disabled {
    background-color: #131A24;
    color: #556275;
    border-color: #1E2837;
}

QPushButton#PrimaryButton {
    background-color: #2F81F7;
    color: #FFFFFF;
    border: 1px solid #388BFD;
}

QPushButton#PrimaryButton:hover {
    background-color: #388BFD;
    border-color: #58A6FF;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1F6FEB;
}

QPushButton#PrimaryButton:disabled {
    background-color: #1A2E4C;
    color: #6B88B4;
    border-color: #213B61;
}

/* Table Header & Scrollable Container */
QFrame#TableHeader {
    background-color: #101620;
    border: 1px solid #1E293B;
    border-radius: 10px;
}

QLabel#HeaderLabel {
    color: #7D8B9F;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
}

QPushButton#HeaderStepButton {
    background-color: transparent;
    color: #7D8B9F;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px 2px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
}

QPushButton#HeaderStepButton:hover {
    background-color: #1A2332;
    color: #E6EDF3;
    border-color: #2B394F;
}

QPushButton#HeaderStepButton:pressed {
    background-color: #151D29;
}

QScrollArea#RepoScrollArea {
    background: transparent;
    border: none;
}

QWidget#RepoScrollContent {
    background: transparent;
}

QLabel#EmptyStateLabel {
    color: #6E7F96;
    font-size: 13.5px;
    padding: 36px;
    background-color: #101620;
    border: 1px dashed #233044;
    border-radius: 12px;
}

/* Repo Row Card */
QFrame#RepoRowCard {
    background-color: #121923;
    border: 1px solid #1F2A3C;
    border-radius: 10px;
}

QFrame#RepoRowCard:hover {
    border-color: #2F405B;
    background-color: #151D29;
}

QLabel#RepoNameLabel {
    color: #F0F6FC;
    font-size: 13.5px;
    font-weight: 600;
}

QLabel#RepoPathLabel {
    color: #6E7F96;
    font-size: 11px;
}

/* Row Micro Action Buttons */
QPushButton#RowIconButton {
    background-color: transparent;
    color: #7D8B9F;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
    font-size: 11px;
    font-weight: 700;
}

QPushButton#RowIconButton:hover {
    background-color: #1E293B;
    color: #E6EDF3;
    border-color: #2E3D54;
}

QPushButton#RowIconButton:disabled {
    color: #334155;
    background-color: transparent;
    border-color: transparent;
}

QPushButton#RowDeleteButton {
    background-color: transparent;
    color: #6E7F96;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#RowDeleteButton:hover {
    background-color: #2D161C;
    color: #F85149;
    border-color: #5C232C;
}

/* Custom Checkbox */
QCheckBox {
    spacing: 0px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1.5px solid #334155;
    background-color: #0E141D;
}

QCheckBox::indicator:hover {
    border-color: #58A6FF;
}

QCheckBox::indicator:checked {
    background-color: #2F81F7;
    border-color: #388BFD;
}

QCheckBox::indicator:disabled {
    background-color: #121821;
    border-color: #1E293B;
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
    background-color: #1A2332;
    color: #8B98AB;
    border: 1px solid #2A374C;
}

QPushButton#StatusBadge[status="running"] {
    background-color: #132847;
    color: #79C0FF;
    border: 1px solid #2F81F7;
}

QPushButton#StatusBadge[status="success"] {
    background-color: #122B1E;
    color: #56D364;
    border: 1px solid #238636;
}

QPushButton#StatusBadge[status="warning"] {
    background-color: #2C2210;
    color: #E3B341;
    border: 1px solid #9E6A03;
}

QPushButton#StatusBadge[status="error"] {
    background-color: #301519;
    color: #FF7B72;
    border: 1px solid #DA3633;
}

/* Commit Inline Bar */
QFrame#CommitBar {
    background-color: #0E1520;
    border-top: 1px solid #1E293B;
}

QLabel#CommitHintLabel {
    color: #8B98AB;
    font-size: 11.5px;
    font-weight: 600;
}

QLineEdit#CommitInput {
    background-color: #151E2B;
    color: #E6EDF3;
    border: 1px solid #2A384D;
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 12px;
}

QLineEdit#CommitInput:focus {
    border-color: #2F81F7;
    background-color: #172231;
}

/* Accordion Log Drawer */
QFrame#AccordionDrawer {
    background-color: #0A0E14;
    border-top: 1px solid #1E293B;
    border-bottom-left-radius: 9px;
    border-bottom-right-radius: 9px;
}

QPlainTextEdit#LogOutput {
    background-color: transparent;
    color: #B6C2D2;
    border: none;
    font-family: "Cascadia Mono", "Consolas", "Courier New", monospace;
    font-size: 11.5px;
    selection-background-color: #1F6FEB;
}

/* Scrollbar */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 0;
}

QScrollBar::handle:vertical {
    background: #273449;
    border-radius: 4px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background: #3A4C69;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
