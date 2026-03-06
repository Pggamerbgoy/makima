"""Tab manager — handles multiple open editor tabs."""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QMessageBox, QFileDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon
from editor.code_editor import CodeEditor
from editor.find_replace import FindReplaceBar
from editor.themes import get_theme

UNTITLED_COUNTER = [0]


def _untitled():
    UNTITLED_COUNTER[0] += 1
    return f"untitled-{UNTITLED_COUNTER[0]}"


class EditorTab(QWidget):
    """One tab = editor + find/replace bar."""
    stats_changed = pyqtSignal()

    def __init__(self, file_path=None, content="", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.editor = CodeEditor(file_path=file_path)
        if content:
            self.editor.setText(content)
            self.editor.mark_saved()
        elif file_path and os.path.isfile(file_path):
            try:
                with open(file_path, encoding="utf-8", errors="replace") as f:
                    self.editor.setText(f.read())
                self.editor.mark_saved()
            except Exception as e:
                self.editor.setText(f"# Error opening file: {e}")

        self.find_bar = FindReplaceBar(editor=self.editor)

        layout.addWidget(self.editor)
        layout.addWidget(self.find_bar)

        self.editor.cursorPositionChanged.connect(self.stats_changed)

    def save(self):
        if not self.file_path:
            return self.save_as()
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(self.editor.text())
            self.editor.mark_saved()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            return False

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save As", self.file_path or "")
        if path:
            self.file_path = path
            self.editor.file_path = path
            self.editor._set_lexer_for_file(path)
            return self.save()
        return False

    @property
    def is_modified(self):
        return self.editor.is_modified

    def tab_label(self):
        name = os.path.basename(self.file_path) if self.file_path else _untitled()
        return ("● " if self.is_modified else "") + name


class TabManager(QWidget):
    """Manages all open editor tabs."""
    active_editor_changed = pyqtSignal(object)  # CodeEditor or None
    stats_changed = pyqtSignal()
    title_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._open_paths = {}  # path -> tab index
        self._setup_ui()

    def _setup_ui(self):
        t = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        # Open a welcome/untitled tab
        self.new_tab()

    def new_tab(self, file_path=None, content=""):
        tab = EditorTab(file_path=file_path, content=content)
        tab.editor.modified_changed.connect(lambda _: self._update_tab_label(tab))
        tab.stats_changed.connect(self.stats_changed)

        label = tab.tab_label()
        idx = self.tabs.addTab(tab, label)
        self.tabs.setCurrentIndex(idx)
        if file_path:
            self._open_paths[file_path] = idx
        tab.editor.setFocus()
        return tab

    def open_file(self, path):
        # If already open, switch to it
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, EditorTab) and tab.file_path == path:
                self.tabs.setCurrentIndex(i)
                return tab
        return self.new_tab(file_path=path)

    def _close_tab(self, idx):
        tab = self.tabs.widget(idx)
        if isinstance(tab, EditorTab) and tab.is_modified:
            r = QMessageBox.question(
                self, "Unsaved Changes",
                f"Save '{tab.tab_label().lstrip('● ')}'?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if r == QMessageBox.StandardButton.Save:
                if not tab.save():
                    return
            elif r == QMessageBox.StandardButton.Cancel:
                return

        if isinstance(tab, EditorTab) and tab.file_path in self._open_paths:
            del self._open_paths[tab.file_path]

        self.tabs.removeTab(idx)
        if self.tabs.count() == 0:
            self.new_tab()

    def _on_tab_changed(self, idx):
        tab = self.tabs.widget(idx)
        if isinstance(tab, EditorTab):
            self.active_editor_changed.emit(tab.editor)
            self.stats_changed.emit()
            name = os.path.basename(tab.file_path) if tab.file_path else "Untitled"
            self.title_changed.emit(name)
        else:
            self.active_editor_changed.emit(None)

    def _update_tab_label(self, tab):
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) is tab:
                self.tabs.setTabText(i, tab.tab_label())
                break

    def current_tab(self):
        tab = self.tabs.currentWidget()
        return tab if isinstance(tab, EditorTab) else None

    def current_editor(self):
        tab = self.current_tab()
        return tab.editor if tab else None

    def save_current(self):
        tab = self.current_tab()
        if tab:
            tab.save()

    def save_current_as(self):
        tab = self.current_tab()
        if tab:
            tab.save_as()
            self._update_tab_label(tab)

    def save_all(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, EditorTab) and tab.is_modified:
                tab.save()
                self._update_tab_label(tab)

    def close_current(self):
        self._close_tab(self.tabs.currentIndex())

    def find_bar(self):
        tab = self.current_tab()
        return tab.find_bar if tab else None

    def refresh_all_themes(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, EditorTab):
                tab.editor.refresh_theme()
