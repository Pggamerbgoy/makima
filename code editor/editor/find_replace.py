"""Find & Replace panel widget."""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from editor.themes import get_theme


class FindReplaceBar(QWidget):
    closed = pyqtSignal()
    search_changed = pyqtSignal(str)

    def __init__(self, editor=None, parent=None):
        super().__init__(parent)
        self._editor = editor
        self._match_count = 0
        self._setup_ui()
        self.hide()

    def set_editor(self, editor):
        self._editor = editor

    def _setup_ui(self):
        t = get_theme()
        self.setStyleSheet(f"""
            QWidget {{ background: {t['bg2']}; border-top: 1px solid {t['border']}; }}
            QLabel {{ color: {t['text2']}; font-size: 11px; background: transparent; border: none; }}
            QCheckBox {{ color: {t['text2']}; font-size: 11px; }}
            QCheckBox::indicator {{
                width: 13px; height: 13px; border-radius: 2px;
                border: 1px solid {t['border']}; background: {t['bg3']};
            }}
            QCheckBox::indicator:checked {{
                background: {t['accent']}; border-color: {t['accent']};
            }}
        """)
        self.setFixedHeight(82)

        main = QVBoxLayout(self)
        main.setContentsMargins(12, 6, 12, 6)
        main.setSpacing(5)

        # Row 1: Find
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        find_lbl = QLabel("Find:")
        find_lbl.setFixedWidth(48)
        row1.addWidget(find_lbl)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Search text...")
        self.find_input.setFixedHeight(26)
        self.find_input.textChanged.connect(self._on_find_changed)
        self.find_input.returnPressed.connect(self.find_next)
        row1.addWidget(self.find_input)

        self.match_label = QLabel("No results")
        self.match_label.setFixedWidth(70)
        self.match_label.setStyleSheet(f"color: {t['text3']}; font-size: 10px; background: transparent;")
        row1.addWidget(self.match_label)

        for lbl, tip, fn in [("↑", "Previous", self.find_prev), ("↓", "Next", self.find_next)]:
            btn = self._make_btn(lbl, tip, fn, small=True)
            row1.addWidget(btn)

        close_btn = self._make_btn("✕", "Close", self.close_bar, small=True)
        row1.addWidget(close_btn)

        main.addLayout(row1)

        # Row 2: Replace + options
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        repl_lbl = QLabel("Replace:")
        repl_lbl.setFixedWidth(48)
        row2.addWidget(repl_lbl)

        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        self.replace_input.setFixedHeight(26)
        row2.addWidget(self.replace_input)

        self.case_cb = QCheckBox("Aa")
        self.case_cb.setToolTip("Case sensitive")
        self.case_cb.stateChanged.connect(self._on_find_changed)
        row2.addWidget(self.case_cb)

        self.whole_cb = QCheckBox("W")
        self.whole_cb.setToolTip("Whole word")
        self.whole_cb.stateChanged.connect(self._on_find_changed)
        row2.addWidget(self.whole_cb)

        self.regex_cb = QCheckBox(".*")
        self.regex_cb.setToolTip("Regular expression")
        self.regex_cb.stateChanged.connect(self._on_find_changed)
        row2.addWidget(self.regex_cb)

        row2.addStretch()

        replace_btn = self._make_btn("Replace", "Replace current", self.replace_one)
        row2.addWidget(replace_btn)

        replace_all_btn = self._make_btn("All", "Replace all", self.replace_all)
        row2.addWidget(replace_all_btn)

        main.addLayout(row2)

    def _make_btn(self, text, tip, fn, small=False):
        t = get_theme()
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.clicked.connect(fn)
        if small:
            btn.setFixedSize(24, 24)
        else:
            btn.setFixedHeight(24)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['bg4']}; border: 1px solid {t['border']};
                border-radius: 4px; color: {t['text2']}; font-size: 11px;
                padding: 0 8px;
            }}
            QPushButton:hover {{ background: {t['accent']}; color: #fff; border-color: {t['accent']}; }}
        """)
        return btn

    def _on_find_changed(self, text=None):
        if self._editor and self.find_input.text():
            found = self._editor.find_text(
                self.find_input.text(),
                case=self.case_cb.isChecked(),
                whole=self.whole_cb.isChecked(),
                regex=self.regex_cb.isChecked()
            )
            if not found:
                self.match_label.setText("No results")
                self.find_input.setStyleSheet(
                    f"border: 1px solid {get_theme()['red']}; background: {get_theme()['bg3']};"
                    f" border-radius: 6px; padding: 5px 10px; color: {get_theme()['text']};"
                )
            else:
                self.find_input.setStyleSheet("")
                self.match_label.setText("Found")

    def find_next(self):
        if self._editor:
            text = self.find_input.text()
            if text:
                found = self._editor.find_text(
                    text,
                    case=self.case_cb.isChecked(),
                    whole=self.whole_cb.isChecked(),
                    regex=self.regex_cb.isChecked(),
                    forward=True
                )
                if not found:
                    # Wrap around
                    self._editor.find_text(text, case=self.case_cb.isChecked(),
                                           whole=self.whole_cb.isChecked(),
                                           regex=self.regex_cb.isChecked())

    def find_prev(self):
        if self._editor:
            text = self.find_input.text()
            if text:
                self._editor.find_text(
                    text,
                    case=self.case_cb.isChecked(),
                    whole=self.whole_cb.isChecked(),
                    regex=self.regex_cb.isChecked(),
                    forward=False
                )

    def replace_one(self):
        if self._editor:
            self._editor.replace_text(
                self.find_input.text(),
                self.replace_input.text(),
                case=self.case_cb.isChecked(),
                whole=self.whole_cb.isChecked(),
                regex=self.regex_cb.isChecked()
            )

    def replace_all(self):
        if self._editor:
            count = self._editor.replace_all(
                self.find_input.text(),
                self.replace_input.text(),
                case=self.case_cb.isChecked(),
                whole=self.whole_cb.isChecked(),
                regex=self.regex_cb.isChecked()
            )
            self.match_label.setText(f"{count} replaced")

    def open_find(self, text=""):
        self.show()
        if text:
            self.find_input.setText(text)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def open_replace(self, text=""):
        self.show()
        if text:
            self.find_input.setText(text)
        self.replace_input.setFocus()

    def close_bar(self):
        self.hide()
        if self._editor:
            self._editor.setFocus()
        self.closed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
        else:
            super().keyPressEvent(event)
