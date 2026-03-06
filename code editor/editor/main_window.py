"""Main application window for Volt Editor."""
import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QLabel, QToolBar, QMenuBar,
    QMenu, QFileDialog, QInputDialog, QMessageBox,
    QComboBox, QPushButton, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import (
    QAction, QFont, QKeySequence, QIcon, QColor
)
from editor.themes import get_theme, set_theme, build_stylesheet, THEMES
from editor.file_explorer import FileExplorer
from editor.tab_manager import TabManager
from editor.terminal import TerminalPanel
from editor.chat_panel import ChatPanel
from editor.find_replace import FindReplaceBar
from editor.editor_bridge import EditorBridge

import qtawesome as qta

ICON_MAP = {
    "new":     "fa5s.file",
    "open":    "fa5s.folder-open",
    "save":    "fa5s.save",
    "saveall": "fa5s.hdd",
    "run":     "fa5s.play",
    "stop":    "fa5s.stop",
    "find":    "fa5s.search",
    "replace": "fa5s.sync",
    "format":  "fa5s.magic",
    "comment": "fa5s.hashtag",
    "undo":    "fa5s.undo",
    "redo":    "fa5s.redo",
    "split":   "fa5s.columns",
    "zen":     "fa5s.expand",
    "ai":      "fa5s.robot",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._zen_mode = False
        self._prev_sidebar_visible = True
        self._prev_bottom_visible = True
        self._setup_window()
        self._apply_theme()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_layout()
        self._setup_statusbar()
        self._connect_signals()
        self._setup_editor_bridge()
        self._update_stats()

    # ─── Window Setup ──────────────────────────────────────────
    def _setup_window(self):
        self.setWindowTitle("Volt — Code Editor")
        self.resize(1400, 900)
        self.setMinimumSize(800, 600)

    def _apply_theme(self):
        t = get_theme()
        self.setStyleSheet(build_stylesheet(t))

    # ─── Menu Bar ──────────────────────────────────────────────
    def _setup_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "New File",        "Ctrl+N",    self._new_file)
        self._add_action(file_menu, "Open File...",    "Ctrl+O",    self._open_file)
        self._add_action(file_menu, "Open Folder...",  "Ctrl+Shift+O", self._open_folder)
        file_menu.addSeparator()
        self._add_action(file_menu, "Save",            "Ctrl+S",    self._save)
        self._add_action(file_menu, "Save As...",      "Ctrl+Shift+S", self._save_as)
        self._add_action(file_menu, "Save All",        "Ctrl+Alt+S", self._save_all)
        file_menu.addSeparator()
        self._add_action(file_menu, "Close Tab",       "Ctrl+W",    self._close_tab)
        file_menu.addSeparator()
        self._add_action(file_menu, "Exit",            "Ctrl+Q",    self.close)

        # Edit
        edit_menu = mb.addMenu("&Edit")
        self._add_action(edit_menu, "Undo",                 "Ctrl+Z",         self._undo)
        self._add_action(edit_menu, "Redo",                 "Ctrl+Shift+Z",   self._redo)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Cut",                  "Ctrl+X",         self._cut)
        self._add_action(edit_menu, "Copy",                 "Ctrl+C",         self._copy)
        self._add_action(edit_menu, "Paste",                "Ctrl+V",         self._paste)
        self._add_action(edit_menu, "Select All",           "Ctrl+A",         self._select_all)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Find",                 "Ctrl+F",         self._find)
        self._add_action(edit_menu, "Replace",              "Ctrl+H",         self._replace)
        self._add_action(edit_menu, "Go to Line...",        "Ctrl+G",         self._goto_line)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Toggle Comment",       "Ctrl+/",         self._toggle_comment)
        self._add_action(edit_menu, "Indent",               "Tab",            self._indent)
        self._add_action(edit_menu, "Unindent",             "Shift+Tab",      self._unindent)
        self._add_action(edit_menu, "Duplicate Line",       "Ctrl+D",         self._duplicate_line)
        self._add_action(edit_menu, "Move Line Up",         "Alt+Up",         self._move_line_up)
        self._add_action(edit_menu, "Move Line Down",       "Alt+Down",       self._move_line_down)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Format Document",      "Shift+Alt+F",    self._format_document)

        # View
        view_menu = mb.addMenu("&View")
        self._add_action(view_menu, "Toggle Sidebar",       "Ctrl+B",         self._toggle_sidebar)
        self._add_action(view_menu, "Toggle Terminal",      "Ctrl+`",         self._toggle_terminal)
        self._add_action(view_menu, "Toggle AI Chat",       "Ctrl+Shift+A",   self._toggle_chat)
        self._add_action(view_menu, "Toggle Zen Mode",      "F11",            self._toggle_zen)
        view_menu.addSeparator()
        self._add_action(view_menu, "Zoom In",              "Ctrl+=",         self._zoom_in)
        self._add_action(view_menu, "Zoom Out",             "Ctrl+-",         self._zoom_out)
        self._add_action(view_menu, "Reset Zoom",           "Ctrl+0",         self._zoom_reset)
        view_menu.addSeparator()
        # Themes submenu
        theme_menu = view_menu.addMenu("Theme")
        for name in THEMES:
            act = QAction(THEMES[name]["name"], self)
            act.triggered.connect(lambda checked, n=name: self._change_theme(n))
            theme_menu.addAction(act)

        # Run
        run_menu = mb.addMenu("&Run")
        self._add_action(run_menu, "Run File",              "F5",             self._run_file)
        self._add_action(run_menu, "Run in Terminal",       "Ctrl+F5",        self._run_in_terminal)
        run_menu.addSeparator()
        self._add_action(run_menu, "New Terminal",          "Ctrl+Shift+`",   self._new_terminal)

        # Help
        help_menu = mb.addMenu("&Help")
        self._add_action(help_menu, "Keyboard Shortcuts",   "Ctrl+Shift+P",   self._show_shortcuts)
        self._add_action(help_menu, "About Volt",           "",               self._about)

    def _add_action(self, menu, name, shortcut, fn):
        act = QAction(name, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(fn)
        menu.addAction(act)
        return act

    # ─── Toolbar ───────────────────────────────────────────────
    def _setup_toolbar(self):
        t = get_theme()
        tb = QToolBar("Main Toolbar")
        tb.setIconSize(QSize(18, 18))
        tb.setMovable(False)
        tb.setFloatable(False)
        self.addToolBar(tb)

        # Logo
        logo = QLabel(" ⚡ VOLT ")
        logo.setStyleSheet(f"color: {t['accent2']}; font-size: 14px; font-weight: 800; letter-spacing: 3px; padding: 0 8px;")
        tb.addWidget(logo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {t['border']}; margin: 6px 4px;")
        tb.addWidget(sep)

        def tbtn(icon_name, tip, fn):
            # Resolve icon from map if it's a key
            qicon_name = ICON_MAP.get(icon_name, icon_name)
            icon = qta.icon(qicon_name, color=t['text2'], color_active=t['accent'])
            
            btn = QPushButton()
            btn._icon_name = icon_name # Store for refresh
            btn.setIcon(icon)
            btn.setIconSize(QSize(18, 18))
            btn.setFixedSize(32, 32)
            btn.setToolTip(tip)
            btn.clicked.connect(fn)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; border-radius: 6px;
                }}
                QPushButton:hover {{ background: {t['bg4']}; }}
                QPushButton:pressed {{ background: {t['accent']}; }}
            """)
            return btn

        for icon, tip, fn in [
            ("new", "New File (Ctrl+N)",    self._new_file),
            ("open", "Open File (Ctrl+O)",   self._open_file),
            ("save", "Save (Ctrl+S)",        self._save),
        ]:
            tb.addWidget(tbtn(icon, tip, fn))

        tb.addSeparator()
        for icon, tip, fn in [
            ("undo", "Undo (Ctrl+Z)",         self._undo),
            ("redo", "Redo (Ctrl+Shift+Z)",   self._redo),
        ]:
            tb.addWidget(tbtn(icon, tip, fn))

        tb.addSeparator()
        for icon, tip, fn in [
            ("find", "Find (Ctrl+F)",         self._find),
            ("replace", "Replace (Ctrl+H)",      self._replace),
        ]:
            tb.addWidget(tbtn(icon, tip, fn))

        tb.addSeparator()
        for icon, tip, fn in [
            ("run", "Run File (F5)",          self._run_file),
            ("format", "Format Document",        self._format_document),
            ("comment", "Toggle Comment (Ctrl+/)",  self._toggle_comment),
        ]:
            tb.addWidget(tbtn(icon, tip, fn))

        tb.addSeparator()
        for icon, tip, fn in [
            ("zen", "Zen Mode (F11)",         self._toggle_zen),
            ("ai", "AI Chat (Ctrl+Shift+A)", self._toggle_chat),
        ]:
            tb.addWidget(tbtn(icon, tip, fn))

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        # Theme picker
        self.theme_combo = QComboBox()
        self.theme_combo.setFixedHeight(26)
        self.theme_combo.setFixedWidth(100)
        for name, td in THEMES.items():
            self.theme_combo.addItem(td["name"], name)
        self.theme_combo.currentIndexChanged.connect(
            lambda i: self._change_theme(self.theme_combo.itemData(i))
        )
        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                background: {t['bg3']}; border: 1px solid {t['border']};
                border-radius: 5px; color: {t['text2']}; font-size: 11px; padding: 0 8px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {t['bg3']}; color: {t['text']};
                selection-background-color: {t['accent']};
            }}
        """)
        tb.addWidget(self.theme_combo)

        self.toolbar = tb

    def _refresh_icons(self):
        """Re-apply icons to toolbar buttons with current theme colors."""
        t = get_theme()
        # The toolbar actions are added via widgets (buttons)
        for i in range(self.toolbar.layout().count()):
            item = self.toolbar.layout().itemAt(i)
            widget = item.widget()
            if isinstance(widget, QPushButton) and hasattr(widget, '_icon_name'):
                qicon_name = ICON_MAP.get(widget._icon_name, widget._icon_name)
                icon = qta.icon(qicon_name, color=t['text2'], color_active=t['accent'])
                widget.setIcon(icon)

    # ─── Layout ────────────────────────────────────────────────
    def _setup_layout(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Horizontal splitter: sidebar | editor area | chat
        self.h_split = QSplitter(Qt.Orientation.Horizontal)
        self.h_split.setHandleWidth(2)

        # Left sidebar
        self.file_explorer = FileExplorer()
        self.file_explorer.setMinimumWidth(160)
        self.file_explorer.setMaximumWidth(400)
        self.h_split.addWidget(self.file_explorer)

        # Center: editor + bottom panel (vertical splitter)
        self.v_split = QSplitter(Qt.Orientation.Vertical)
        self.v_split.setHandleWidth(2)

        # Tab manager (code editors)
        self.tab_manager = TabManager()
        self.v_split.addWidget(self.tab_manager)

        # Bottom panel (terminal)
        self.terminal = TerminalPanel()
        self.terminal.setMinimumHeight(80)
        self.terminal.setMaximumHeight(500)
        self.v_split.addWidget(self.terminal)

        self.v_split.setSizes([600, 220])
        self.h_split.addWidget(self.v_split)

        # Right: AI Chat
        self.chat_panel = ChatPanel()
        self.chat_panel.setMinimumWidth(260)
        self.chat_panel.setMaximumWidth(520)
        self.h_split.addWidget(self.chat_panel)

        self.h_split.setSizes([220, 900, 0])  # Chat hidden by default
        main_layout.addWidget(self.h_split)

    # ─── Status Bar ────────────────────────────────────────────
    def _setup_statusbar(self):
        t = get_theme()
        sb = self.statusBar()

        def status_lbl(text=""):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: rgba(255,255,255,0.85); font-size: 11px; padding: 0 8px; font-family: 'JetBrains Mono';")
            return lbl

        self.status_branch = status_lbl("main")
        self.status_file = status_lbl("No file")
        self.status_pos = status_lbl("Ln 1, Col 1")
        self.status_lang = status_lbl("Plain Text")
        self.status_enc = status_lbl("UTF-8")
        self.status_eol = status_lbl("LF")
        self.status_sel = status_lbl("")
        self.status_msg = status_lbl("")

        sb.addWidget(QLabel("  ⎇ "))
        sb.addWidget(self.status_branch)
        sb.addPermanentWidget(self.status_msg)
        sb.addPermanentWidget(self.status_sel)
        sb.addPermanentWidget(self.status_lang)
        sb.addPermanentWidget(self.status_enc)
        sb.addPermanentWidget(self.status_eol)
        sb.addPermanentWidget(self.status_pos)

        # Flash message timer
        self._msg_timer = QTimer()
        self._msg_timer.setSingleShot(True)
        self._msg_timer.timeout.connect(lambda: self.status_msg.setText(""))

    def _flash_msg(self, msg, ms=3000):
        self.status_msg.setText(msg)
        self._msg_timer.start(ms)

    # ─── Signals ───────────────────────────────────────────────
    def _connect_signals(self):
        self.file_explorer.file_opened.connect(self._open_path)
        self.tab_manager.active_editor_changed.connect(self._on_editor_changed)
        self.tab_manager.stats_changed.connect(self._update_stats)
        self.tab_manager.title_changed.connect(lambda t: self.setWindowTitle(f"{t} — Volt"))
        self.chat_panel.insert_code.connect(self._inject_code_to_chat)

    def _setup_editor_bridge(self):
        """Create the AI ↔ Editor bridge and attach it to the chat panel."""
        self.editor_bridge = EditorBridge(main_window=self)
        self.chat_panel.set_bridge(self.editor_bridge)

    def _on_editor_changed(self, editor):
        find_bar = self.tab_manager.find_bar()
        if find_bar:
            find_bar.set_editor(editor)
        self._update_stats()

    def _update_stats(self):
        editor = self.tab_manager.current_editor()
        if not editor:
            return
        line, col, lines, chars, sel = editor.get_stats()
        self.status_pos.setText(f"Ln {line}, Col {col}")
        if sel:
            self.status_sel.setText(f"Sel {sel}")
        else:
            self.status_sel.setText("")

        # Language
        fp = editor.file_path
        if fp:
            ext = os.path.splitext(fp)[1].lower()
            lang_map = {
                ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".jsx": "React JSX", ".tsx": "React TSX",
                ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
                ".json": "JSON", ".md": "Markdown", ".sh": "Shell",
                ".cpp": "C++", ".c": "C", ".h": "C/C++ Header",
                ".sql": "SQL", ".yaml": "YAML", ".yml": "YAML",
                ".xml": "XML", ".txt": "Plain Text",
            }
            self.status_lang.setText(lang_map.get(ext, ext[1:].upper() if ext else "Plain Text"))
            self.status_file.setText(os.path.basename(fp))
        else:
            self.status_lang.setText("Plain Text")

    # ─── File Actions ──────────────────────────────────────────
    def _new_file(self):
        self.tab_manager.new_tab()

    def _open_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open File", "",
            "All Files (*);;Python (*.py);;JavaScript (*.js);;HTML (*.html);;CSS (*.css);;JSON (*.json)"
        )
        for p in paths:
            self._open_path(p)

    def _open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if path:
            self.file_explorer.set_root(path)

    def _open_path(self, path):
        self.tab_manager.open_file(path)
        self.terminal.set_cwd(os.path.dirname(path))

    def _save(self):
        self.tab_manager.save_current()
        self._flash_msg("✓ Saved")

    def _save_as(self):
        self.tab_manager.save_current_as()

    def _save_all(self):
        self.tab_manager.save_all()
        self._flash_msg("✓ All files saved")

    def _close_tab(self):
        self.tab_manager.close_current()

    # ─── Edit Actions ──────────────────────────────────────────
    def _undo(self):
        e = self.tab_manager.current_editor()
        if e: e.undo()

    def _redo(self):
        e = self.tab_manager.current_editor()
        if e: e.redo()

    def _cut(self):
        e = self.tab_manager.current_editor()
        if e: e.cut()

    def _copy(self):
        e = self.tab_manager.current_editor()
        if e: e.copy()

    def _paste(self):
        e = self.tab_manager.current_editor()
        if e: e.paste()

    def _select_all(self):
        e = self.tab_manager.current_editor()
        if e: e.selectAll()

    def _find(self):
        fb = self.tab_manager.find_bar()
        if fb:
            e = self.tab_manager.current_editor()
            sel = e.selectedText() if e else ""
            fb.open_find(sel)

    def _replace(self):
        fb = self.tab_manager.find_bar()
        if fb:
            e = self.tab_manager.current_editor()
            sel = e.selectedText() if e else ""
            fb.open_replace(sel)

    def _goto_line(self):
        e = self.tab_manager.current_editor()
        if not e:
            return
        max_line = e.lines()
        line, ok = QInputDialog.getInt(self, "Go to Line", f"Line (1–{max_line}):", 1, 1, max_line)
        if ok:
            e.goto_line(line)

    def _toggle_comment(self):
        e = self.tab_manager.current_editor()
        if e: e.toggle_comment()

    def _indent(self):
        e = self.tab_manager.current_editor()
        if e: e.indent_selection()

    def _unindent(self):
        e = self.tab_manager.current_editor()
        if e: e.unindent_selection()

    def _duplicate_line(self):
        e = self.tab_manager.current_editor()
        if e: e.duplicate_line()

    def _move_line_up(self):
        e = self.tab_manager.current_editor()
        if e: e.move_line_up()

    def _move_line_down(self):
        e = self.tab_manager.current_editor()
        if e: e.move_line_down()

    def _format_document(self):
        e = self.tab_manager.current_editor()
        if not e:
            return
        fp = e.file_path
        if not fp:
            self._flash_msg("⚠ Save file first to format")
            return
        ext = os.path.splitext(fp)[1].lower()
        cmd_map = {
            ".py": f"black {fp}",
            ".js": f"prettier --write {fp}",
            ".ts": f"prettier --write {fp}",
            ".jsx": f"prettier --write {fp}",
            ".tsx": f"prettier --write {fp}",
            ".json": f"prettier --write {fp}",
            ".css": f"prettier --write {fp}",
            ".html": f"prettier --write {fp}",
        }
        cmd = cmd_map.get(ext)
        if cmd:
            # Save first, then format
            self.tab_manager.save_current()
            self.terminal.run_command(cmd)
            # Reload after a delay
            QTimer.singleShot(1500, lambda: self._reload_current_file(fp, e))
        else:
            self._flash_msg(f"No formatter for {ext}")

    def _reload_current_file(self, path, editor):
        try:
            with open(path, encoding="utf-8") as f:
                editor.setText(f.read())
            editor.mark_saved()
            self._flash_msg("✓ Formatted")
        except Exception:
            pass

    # ─── View Actions ──────────────────────────────────────────
    def _toggle_sidebar(self):
        visible = self.file_explorer.isVisible()
        self.file_explorer.setVisible(not visible)

    def _toggle_terminal(self):
        visible = self.terminal.isVisible()
        self.terminal.setVisible(not visible)
        if not visible:
            self.terminal.tabs.currentWidget() and self.terminal.tabs.currentWidget().input.setFocus()

    def _toggle_chat(self):
        sizes = self.h_split.sizes()
        if sizes[2] < 50:
            self.h_split.setSizes([sizes[0], sizes[1] - 320, 320])
        else:
            self.h_split.setSizes([sizes[0], sizes[1] + sizes[2], 0])

    def _toggle_zen(self):
        self._zen_mode = not self._zen_mode
        if self._zen_mode:
            self._prev_sidebar_visible = self.file_explorer.isVisible()
            self._prev_bottom_visible = self.terminal.isVisible()
            self.file_explorer.hide()
            self.terminal.hide()
            self.toolbar.hide()
            self.menuBar().hide()
            self.statusBar().hide()
            self.showFullScreen()
        else:
            self.file_explorer.setVisible(self._prev_sidebar_visible)
            self.terminal.setVisible(self._prev_bottom_visible)
            self.toolbar.show()
            self.menuBar().show()
            self.statusBar().show()
            self.showNormal()

    def _zoom_in(self):
        e = self.tab_manager.current_editor()
        if e: e.zoomIn(1)

    def _zoom_out(self):
        e = self.tab_manager.current_editor()
        if e: e.zoomOut(1)

    def _zoom_reset(self):
        e = self.tab_manager.current_editor()
        if e: e.zoomTo(0)

    def _change_theme(self, name):
        set_theme(name)
        self._apply_theme()
        self._refresh_icons()
        self.file_explorer.refresh_theme()
        self.tab_manager.refresh_all_themes()
        self._flash_msg(f"Theme: {THEMES[name]['name']}")

    # ─── Run Actions ───────────────────────────────────────────
    def _run_file(self):
        self._save()
        e = self.tab_manager.current_editor()
        if not e or not e.file_path:
            self._flash_msg("⚠ Save file first")
            return
        fp = e.file_path
        ext = os.path.splitext(fp)[1].lower()
        cmd_map = {
            ".py":  f"python3 {fp}",
            ".js":  f"node {fp}",
            ".ts":  f"ts-node {fp}",
            ".sh":  f"bash {fp}",
            ".rb":  f"ruby {fp}",
            ".php": f"php {fp}",
            ".go":  f"go run {fp}",
            ".rs":  f"cargo run",
        }
        cmd = cmd_map.get(ext, f"echo 'No runner for {ext}'")
        self.terminal.setVisible(True)
        self.terminal.run_command(cmd)

    def _run_in_terminal(self):
        self._run_file()

    def _new_terminal(self):
        self.terminal.setVisible(True)
        self.terminal.new_terminal()

    # ─── AI Chat ───────────────────────────────────────────────
    def _inject_code_to_chat(self, signal):
        e = self.tab_manager.current_editor()
        if e:
            sel = e.selectedText()
            if sel:
                self.chat_panel.inject_code(sel)
            else:
                # Insert full file
                self.chat_panel.inject_code(e.text()[:3000])

    # ─── Help ──────────────────────────────────────────────────
    def _show_shortcuts(self):
        shortcuts = """
<h2 style='font-family:JetBrains Mono'>⚡ Volt Keyboard Shortcuts</h2>
<table style='font-family:JetBrains Mono;font-size:13px;border-collapse:collapse'>
<tr><td style='padding:4px 16px 4px 0;color:#a78bfa'><b>File</b></td></tr>
<tr><td>Ctrl+N</td><td>New File</td></tr>
<tr><td>Ctrl+O</td><td>Open File</td></tr>
<tr><td>Ctrl+S</td><td>Save</td></tr>
<tr><td>Ctrl+Shift+S</td><td>Save As</td></tr>
<tr><td>Ctrl+Alt+S</td><td>Save All</td></tr>
<tr><td>Ctrl+W</td><td>Close Tab</td></tr>
<tr><td></td></tr>
<tr><td style='padding:4px 16px 4px 0;color:#a78bfa'><b>Edit</b></td></tr>
<tr><td>Ctrl+Z</td><td>Undo</td></tr>
<tr><td>Ctrl+Shift+Z</td><td>Redo</td></tr>
<tr><td>Ctrl+F</td><td>Find</td></tr>
<tr><td>Ctrl+H</td><td>Replace</td></tr>
<tr><td>Ctrl+G</td><td>Go to Line</td></tr>
<tr><td>Ctrl+/</td><td>Toggle Comment</td></tr>
<tr><td>Ctrl+D</td><td>Duplicate Line</td></tr>
<tr><td>Alt+Up/Down</td><td>Move Line</td></tr>
<tr><td>Shift+Alt+F</td><td>Format Document</td></tr>
<tr><td></td></tr>
<tr><td style='padding:4px 16px 4px 0;color:#a78bfa'><b>View</b></td></tr>
<tr><td>Ctrl+B</td><td>Toggle Sidebar</td></tr>
<tr><td>Ctrl+`</td><td>Toggle Terminal</td></tr>
<tr><td>Ctrl+Shift+A</td><td>Toggle AI Chat</td></tr>
<tr><td>F11</td><td>Zen Mode</td></tr>
<tr><td>Ctrl+= / Ctrl+-</td><td>Zoom In/Out</td></tr>
<tr><td></td></tr>
<tr><td style='padding:4px 16px 4px 0;color:#a78bfa'><b>Run</b></td></tr>
<tr><td>F5</td><td>Run File</td></tr>
<tr><td>Ctrl+Shift+`</td><td>New Terminal</td></tr>
</table>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setText(shortcuts)
        msg.exec()

    def _about(self):
        QMessageBox.about(self, "About Volt",
            "<h2>⚡ Volt Code Editor</h2>"
            "<p>A professional, fully-featured code editor built with PyQt6 + QScintilla.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Syntax highlighting for 15+ languages</li>"
            "<li>File explorer with drag & drop</li>"
            "<li>Multiple tabs with unsaved indicators</li>"
            "<li>Integrated multi-tab terminal</li>"
            "<li>Find & Replace with regex support</li>"
            "<li>AI agent chat panel (OpenAI, Anthropic, Ollama, custom)</li>"
            "<li>3 built-in themes (Dark, Light, Monokai)</li>"
            "<li>Code folding, auto-indent, brace matching</li>"
            "<li>Code runner (Python, JS, Shell, Go, Ruby, PHP, Rust)</li>"
            "<li>Document formatter (black, prettier)</li>"
            "<li>Zen mode / distraction-free writing</li>"
            "</ul>"
            "<p>Add your own AI agents via ⚙ in the chat panel.</p>"
        )

    # ─── Close ─────────────────────────────────────────────────
    def closeEvent(self, event):
        # Save all modified files prompt
        modified = []
        for i in range(self.tab_manager.tabs.tabs.count()):
            tab = self.tab_manager.tabs.tabs.widget(i)
            from editor.tab_manager import EditorTab
            if isinstance(tab, EditorTab) and tab.is_modified:
                modified.append(tab)

        if modified:
            r = QMessageBox.question(
                self, "Unsaved Changes",
                f"{len(modified)} file(s) have unsaved changes. Save all before exiting?",
                QMessageBox.StandardButton.SaveAll |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if r == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif r == QMessageBox.StandardButton.SaveAll:
                self.tab_manager.save_all()

        event.accept()
