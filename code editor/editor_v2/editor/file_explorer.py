"""File explorer sidebar with tree view."""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeView,
    QPushButton, QLineEdit, QMenu, QInputDialog,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QDir, QSortFilterProxyModel, pyqtSignal, QModelIndex
from PyQt6.QtGui import QFileSystemModel, QAction, QIcon, QFont, QColor
import qtawesome as qta
from editor.themes import get_theme

# Mapping extension-to-icon-info (name, color)
# Colors will be pulled from theme if possible
EXT_ICONS = {
    ".py":   ("fa5b.python",   "#3776AB"),
    ".js":   ("fa5b.js",       "#F7DF1E"),
    ".ts":   ("fa5s.code",     "#3178C6"),
    ".html": ("fa5b.html5",    "#E34F26"),
    ".css":  ("fa5b.css3-alt", "#1572B6"),
    ".json": ("fa5s.terminal", "#F5DE19"),
    ".md":   ("fa5s.file-alt", "#888888"),
    ".txt":  ("fa5s.file-alt", "#BBBBBB"),
    ".sh":   ("fa5s.terminal", "#4EAA25"),
    ".cpp":  ("fa5s.cog",      "#00599C"),
    ".c":    ("fa5s.cog",      "#A8B9CC"),
    ".h":    ("fa5s.cog",      "#A8B9CC"),
    ".yaml": ("fa5s.project-diagram", "#CB171E"),
    ".yml":  ("fa5s.project-diagram", "#CB171E"),
    "dir":   ("fa5s.folder",   "#A78BFA"), # Theme accent 1 normally
}

class IconFileSystemModel(QFileSystemModel):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme

    def data(self, index, role):
        if role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
            info = self.fileInfo(index)
            if info.isDir():
                return qta.icon("fa5s.folder", color=self.theme['accent'])
            
            ext = info.suffix().lower()
            icon_data = EXT_ICONS.get("." + ext)
            if icon_data:
                name, clr = icon_data
                return qta.icon(name, color=clr)
            
            return qta.icon("fa5s.file", color=self.theme['text3'])
            
        return super().data(index, role)

class FileExplorer(QWidget):
    file_opened = pyqtSignal(str)
    root_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = os.path.expanduser("~")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("EXPLORER")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # Path bar
        path_bar = QWidget()
        path_bar.setFixedHeight(32)
        t = get_theme()
        path_bar.setStyleSheet(f"background:{t['bg2']}; border-bottom:1px solid {t['border']};")
        ph = QHBoxLayout(path_bar)
        ph.setContentsMargins(8, 4, 8, 4)
        ph.setSpacing(4)

        self.path_label = QLineEdit(self._root)
        self.path_label.setReadOnly(True)
        self.path_label.setStyleSheet(f"""
            background: transparent; border: none; color: {t['text3']};
            font-size: 10px; font-family: 'JetBrains Mono';
        """)
        ph.addWidget(self.path_label)

        self.open_btn = QPushButton("⊕")
        self.open_btn.setFixedSize(22, 22)
        self.open_btn.setToolTip("Open Folder")
        self.open_btn.clicked.connect(self._open_folder)
        self.open_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {t['text2']};
                font-size: 14px; border-radius: 3px; }}
            QPushButton:hover {{ background: {t['bg4']}; color: {t['text']}; }}
        """)
        ph.addWidget(self.open_btn)

        self.new_file_btn = QPushButton("📄")
        self.new_file_btn.setFixedSize(22, 22)
        self.new_file_btn.setToolTip("New File")
        self.new_file_btn.clicked.connect(self._new_file)
        self.new_file_btn.setStyleSheet(self.open_btn.styleSheet())
        ph.addWidget(self.new_file_btn)

        self.new_dir_btn = QPushButton("📁")
        self.new_dir_btn.setFixedSize(22, 22)
        self.new_dir_btn.setToolTip("New Folder")
        self.new_dir_btn.clicked.connect(self._new_folder)
        self.new_dir_btn.setStyleSheet(self.open_btn.styleSheet())
        ph.addWidget(self.new_dir_btn)

        layout.addWidget(path_bar)

        # Search bar
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search files...")
        self.search.setFixedHeight(28)
        t = get_theme()
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: {t['bg3']}; border: none; border-bottom: 1px solid {t['border']};
                color: {t['text2']}; font-size: 11px; padding: 0 10px;
                font-family: 'JetBrains Mono';
            }}
        """)
        self.search.textChanged.connect(self._filter_changed)
        layout.addWidget(self.search)

        # File system model
        self.model = IconFileSystemModel(t)
        self.model.setRootPath(self._root)
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden)
        self.model.setNameFilterDisables(False)

        # Tree view
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self._root))
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree.setHeaderHidden(True)
        # Hide size/type/date columns
        for col in range(1, 4):
            self.tree.hideColumn(col)
        self.tree.doubleClicked.connect(self._on_double_click)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.tree.setStyleSheet(f"""
            QTreeView {{
                background: {t['bg2']}; border: none;
                color: {t['text2']}; font-size: 12px;
            }}
            QTreeView::item {{ height: 28px; padding-left: 4px; border-radius: 4px; }}
            QTreeView::item:hover {{ background: {t['bg3']}; color: {t['text']}; }}
            QTreeView::item:selected {{ background: {t['bg4']}; color: {t['accent']}; border-left: 2px solid {t['accent']}; }}
        """)
        layout.addWidget(self.tree)

    def refresh_theme(self):
        t = get_theme()
        self.model.theme = t
        self.model.layoutChanged.emit() # Force refresh decoration role calls
        
        # Refresh path bar and search bar styling
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: {t['bg3']}; border: none; border-bottom: 1px solid {t['border']};
                color: {t['text2']}; font-size: 11px; padding: 0 10px;
                font-family: 'JetBrains Mono';
            }}
        """)
        self.tree.setStyleSheet(f"""
            QTreeView {{
                background: {t['bg2']}; border: none;
                color: {t['text2']}; font-size: 12px;
            }}
            QTreeView::item {{ height: 28px; padding-left: 4px; border-radius: 4px; }}
            QTreeView::item:hover {{ background: {t['bg3']}; color: {t['text']}; }}
            QTreeView::item:selected {{ background: {t['bg4']}; color: {t['accent']}; border-left: 2px solid {t['accent']}; }}
        """)
        # Refresh path label etc.
        self.path_label.setStyleSheet(f"""
            background: transparent; border: none; color: {t['text3']};
            font-size: 10px; font-family: 'JetBrains Mono';
        """)

    def set_root(self, path):
        self._root = path
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
        self.path_label.setText(path)
        self.root_changed.emit(path)

    def _open_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "Open Folder", self._root)
        if path:
            self.set_root(path)

    def _new_file(self):
        idx = self.tree.currentIndex()
        if idx.isValid():
            p = self.model.filePath(idx)
            folder = p if os.path.isdir(p) else os.path.dirname(p)
        else:
            folder = self._root
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if ok and name:
            full = os.path.join(folder, name)
            open(full, "w").close()
            self.model.setRootPath(self._root)

    def _new_folder(self):
        idx = self.tree.currentIndex()
        if idx.isValid():
            p = self.model.filePath(idx)
            folder = p if os.path.isdir(p) else os.path.dirname(p)
        else:
            folder = self._root
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name:
            os.makedirs(os.path.join(folder, name), exist_ok=True)

    def _on_double_click(self, index):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            self.file_opened.emit(path)

    def _context_menu(self, pos):
        idx = self.tree.indexAt(pos)
        menu = QMenu(self)
        if idx.isValid():
            path = self.model.filePath(idx)
            is_dir = os.path.isdir(path)
            if not is_dir:
                open_act = QAction("Open", self)
                open_act.triggered.connect(lambda: self.file_opened.emit(path))
                menu.addAction(open_act)
                menu.addSeparator()
            rename_act = QAction("Rename", self)
            rename_act.triggered.connect(lambda: self._rename(idx, path))
            menu.addAction(rename_act)
            delete_act = QAction("Delete", self)
            delete_act.triggered.connect(lambda: self._delete(path, is_dir))
            menu.addAction(delete_act)
            menu.addSeparator()
        new_file = QAction("New File", self)
        new_file.triggered.connect(self._new_file)
        menu.addAction(new_file)
        new_dir = QAction("New Folder", self)
        new_dir.triggered.connect(self._new_folder)
        menu.addAction(new_dir)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _rename(self, idx, path):
        old_name = os.path.basename(path)
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_name)
        if ok and name and name != old_name:
            new_path = os.path.join(os.path.dirname(path), name)
            os.rename(path, new_path)

    def _delete(self, path, is_dir):
        msg = f"Delete {'folder' if is_dir else 'file'} '{os.path.basename(path)}'?"
        r = QMessageBox.question(self, "Confirm Delete", msg)
        if r == QMessageBox.StandardButton.Yes:
            if is_dir:
                import shutil
                shutil.rmtree(path)
            else:
                os.remove(path)

    def _filter_changed(self, text):
        if text:
            self.model.setNameFilters([f"*{text}*"])
            self.model.setNameFilterDisables(False)
        else:
            self.model.setNameFilters([])
