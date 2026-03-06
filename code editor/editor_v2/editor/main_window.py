"""Main window — VS Code / Antigravity layout."""
import os, sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QStatusBar, QLabel, QToolBar, QFileDialog, QInputDialog,
    QMessageBox, QComboBox, QPushButton, QSizePolicy, QFrame,
    QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QFont, QKeySequence, QColor

from editor.themes import get_theme, set_theme, build_stylesheet, THEMES
from editor.file_explorer import FileExplorer
from editor.tab_manager import TabManager
from editor.terminal import TerminalPanel
from editor.chat_panel import ChatPanel


class ActivityBar(QWidget):
    """Thin icon bar on the far left, like VS Code."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("activityBar")
        self.setFixedWidth(48)
        self._setup()

    def _setup(self):
        t = get_theme()
        self.setStyleSheet(f"""
            QWidget#activityBar {{
                background: {t['actbar_bg']};
                border-right: 1px solid {t['actbar_border']};
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._buttons = {}
        top_icons = [
            ("explorer",  "⬜", "Explorer (Ctrl+B)"),
            ("search",    "🔍", "Search (Ctrl+F)"),
            ("git",       "⎇",  "Source Control"),
            ("run",       "▷",  "Run & Debug (F5)"),
            ("extensions","⊞",  "Extensions"),
        ]
        for key, icon, tip in top_icons:
            btn = self._make_btn(icon, tip)
            self._buttons[key] = btn
            lay.addWidget(btn)

        lay.addStretch()

        # Bottom icons
        for icon, tip in [("⚙", "Settings"), ("👤", "Account")]:
            lay.addWidget(self._make_btn(icon, tip))

        # Set explorer active by default
        self._set_active("explorer")

    def _make_btn(self, icon, tip):
        t = get_theme()
        btn = QPushButton(icon)
        btn.setToolTip(tip)
        btn.setFixedSize(48, 48)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-left: 2px solid transparent;
                color: {t['actbar_fg']};
                font-size: 18px;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {t['fg_white']};
                border-left: 2px solid transparent;
            }}
            QPushButton[active="true"] {{
                color: {t['fg_white']};
                border-left: 2px solid {t['accent']};
            }}
        """)
        return btn

    def _set_active(self, key):
        t = get_theme()
        for k, btn in self._buttons.items():
            if k == key:
                btn.setProperty("active", "true")
                btn.setStyleSheet(btn.styleSheet())
            else:
                btn.setProperty("active", "false")
                btn.setStyleSheet(btn.styleSheet())


class BreadcrumbBar(QWidget):
    """File path breadcrumb, like VS Code."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("breadcrumb")
        self.setFixedHeight(22)
        t = get_theme()
        self.setStyleSheet(f"""
            QWidget#breadcrumb {{
                background: {t['bg']};
                border-bottom: 1px solid {t['border']};
            }}
        """)
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(12, 0, 12, 0)
        self._lay.setSpacing(0)
        self._lay.addStretch()

    def set_path(self, path):
        # Clear old labels
        while self._lay.count() > 1:
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not path:
            return

        t = get_theme()
        parts = path.replace("\\", "/").split("/")
        parts = [p for p in parts if p]

        for i, part in enumerate(parts):
            lbl = QLabel(part)
            lbl.setObjectName("breadcrumbLabel")
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {t['fg_dim']};
                    font-size: 12px;
                    background: transparent;
                    padding: 0 2px;
                }}
                QLabel:hover {{ color: {t['fg']}; }}
            """)
            self._lay.insertWidget(i * 2, lbl)
            if i < len(parts) - 1:
                sep = QLabel(" › ")
                sep.setStyleSheet(f"color: {t['fg_dim']}; font-size: 11px; background: transparent;")
                self._lay.insertWidget(i * 2 + 1, sep)

        # Make last part brighter
        last_idx = (len(parts) - 1) * 2
        if last_idx < self._lay.count():
            item = self._lay.itemAt(last_idx)
            if item and item.widget():
                item.widget().setStyleSheet(f"""
                    QLabel {{
                        color: {t['fg']};
                        font-size: 12px;
                        background: transparent;
                        padding: 0 2px;
                    }}
                """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._zen_mode = False
        self._prev_sidebar = True
        self._prev_bottom = True
        self._setup_window()
        self._apply_theme()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_layout()
        self._setup_statusbar()
        self._connect_signals()
        self._update_stats()

    def _setup_window(self):
        self.setWindowTitle("Volt")
        self.resize(1400, 900)
        self.setMinimumSize(800, 600)

    def _apply_theme(self):
        self.setStyleSheet(build_stylesheet(get_theme()))

    # ── Menu ────────────────────────────────────────────────────
    def _setup_menu(self):
        mb = self.menuBar()
        def act(menu, name, shortcut, fn):
            a = QAction(name, self)
            if shortcut: a.setShortcut(QKeySequence(shortcut))
            a.triggered.connect(fn)
            menu.addAction(a)

        # File
        fm = mb.addMenu("File")
        act(fm, "New File",         "Ctrl+N",       self._new_file)
        act(fm, "Open File...",     "Ctrl+O",       self._open_file)
        act(fm, "Open Folder...",   "Ctrl+Shift+O", self._open_folder)
        fm.addSeparator()
        act(fm, "Save",             "Ctrl+S",       self._save)
        act(fm, "Save As...",       "Ctrl+Shift+S", self._save_as)
        act(fm, "Save All",         "Ctrl+Alt+S",   self._save_all)
        fm.addSeparator()
        act(fm, "Close Tab",        "Ctrl+W",       self._close_tab)
        fm.addSeparator()
        act(fm, "Exit",             "Ctrl+Q",       self.close)

        # Edit
        em = mb.addMenu("Edit")
        act(em, "Undo",                 "Ctrl+Z",         self._undo)
        act(em, "Redo",                 "Ctrl+Shift+Z",   self._redo)
        em.addSeparator()
        act(em, "Cut",                  "Ctrl+X",         self._cut)
        act(em, "Copy",                 "Ctrl+C",         self._copy)
        act(em, "Paste",                "Ctrl+V",         self._paste)
        act(em, "Select All",           "Ctrl+A",         self._select_all)
        em.addSeparator()
        act(em, "Find",                 "Ctrl+F",         self._find)
        act(em, "Replace",              "Ctrl+H",         self._replace)
        act(em, "Go to Line...",        "Ctrl+G",         self._goto_line)
        em.addSeparator()
        act(em, "Toggle Comment",       "Ctrl+/",         self._toggle_comment)
        act(em, "Duplicate Line",       "Ctrl+D",         self._duplicate_line)
        act(em, "Move Line Up",         "Alt+Up",         self._move_line_up)
        act(em, "Move Line Down",       "Alt+Down",       self._move_line_down)
        act(em, "Indent Lines",         "Tab",            self._indent)
        act(em, "Outdent Lines",        "Shift+Tab",      self._unindent)
        em.addSeparator()
        act(em, "Format Document",      "Shift+Alt+F",    self._format_document)

        # View
        vm = mb.addMenu("View")
        act(vm, "Toggle Sidebar",       "Ctrl+B",         self._toggle_sidebar)
        act(vm, "Toggle Terminal",      "Ctrl+`",         self._toggle_terminal)
        act(vm, "Toggle AI Chat",       "Ctrl+Shift+A",   self._toggle_chat)
        act(vm, "Zen Mode",             "F11",            self._toggle_zen)
        vm.addSeparator()
        act(vm, "Zoom In",              "Ctrl+=",         self._zoom_in)
        act(vm, "Zoom Out",             "Ctrl+-",         self._zoom_out)
        act(vm, "Reset Zoom",           "Ctrl+0",         self._zoom_reset)
        vm.addSeparator()
        tm = vm.addMenu("Color Theme")
        for key, td in THEMES.items():
            a = QAction(td["name"], self)
            a.triggered.connect(lambda c, k=key: self._change_theme(k))
            tm.addAction(a)

        # Run
        rm = mb.addMenu("Run")
        act(rm, "Run File",             "F5",             self._run_file)
        act(rm, "Run in Terminal",      "Ctrl+F5",        self._run_file)
        rm.addSeparator()
        act(rm, "New Terminal",         "Ctrl+Shift+`",   self._new_terminal)

        # Help
        hm = mb.addMenu("Help")
        act(hm, "Keyboard Shortcuts",   "Ctrl+Shift+P",   self._show_shortcuts)
        act(hm, "About Volt",           "",               self._about)

    # ── Toolbar ────────────────────────────────────────────────
    def _setup_toolbar(self):
        t = get_theme()
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)

        def tbtn(text, tip, fn):
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setFixedSize(28, 28)
            btn.clicked.connect(fn)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; border-radius: 3px;
                    color: {t['fg']}; font-size: 14px; padding: 0;
                }}
                QPushButton:hover {{ background: {t['bg_hover']}; }}
                QPushButton:pressed {{ background: {t['bg_selection']}; }}
            """)
            return btn

        # Logo label
        logo = QLabel("  Volt  ")
        logo.setStyleSheet(f"""
            color: {t['fg_white']};
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 1px;
            padding: 0 4px;
            background: transparent;
        """)
        tb.addWidget(logo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(18)
        sep.setStyleSheet(f"color: {t['border']}; margin: 0 4px;")
        tb.addWidget(sep)

        groups = [
            [("📄", "New (Ctrl+N)", self._new_file),
             ("📂", "Open (Ctrl+O)", self._open_file),
             ("💾", "Save (Ctrl+S)", self._save)],
            [("↩", "Undo", self._undo), ("↪", "Redo", self._redo)],
            [("🔍", "Find (Ctrl+F)", self._find)],
            [("▶", "Run (F5)", self._run_file),
             ("✨", "Format (Shift+Alt+F)", self._format_document)],
        ]
        for group in groups:
            for icon, tip, fn in group:
                tb.addWidget(tbtn(icon, tip, fn))
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.Shape.VLine)
            sep2.setFixedHeight(18)
            sep2.setStyleSheet(f"color: {t['border']}; margin: 0 4px;")
            tb.addWidget(sep2)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(110)
        self.theme_combo.setFixedHeight(24)
        for key, td in THEMES.items():
            self.theme_combo.addItem(td["name"], key)
        self.theme_combo.currentIndexChanged.connect(
            lambda i: self._change_theme(self.theme_combo.itemData(i))
        )
        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                background: {t['bg_input']}; border: 1px solid {t['border']};
                border-radius: 2px; color: {t['fg_dim']}; font-size: 12px; padding: 0 8px;
            }}
            QComboBox:focus {{ border-color: {t['border_focus']}; }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox QAbstractItemView {{
                background: {t['bg_dropdown']}; border: 1px solid {t['border']};
                color: {t['fg']}; selection-background-color: {t['accent']};
                selection-color: {t['fg_white']};
            }}
        """)
        tb.addWidget(self.theme_combo)
        tb.addWidget(tbtn("🤖", "AI Chat (Ctrl+Shift+A)", self._toggle_chat))
        self.toolbar = tb

    # ── Layout ──────────────────────────────────────────────────
    def _setup_layout(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Activity bar
        self.activity_bar = ActivityBar()
        root.addWidget(self.activity_bar)

        # Main area
        main_area = QWidget()
        main_lay = QVBoxLayout(main_area)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Horizontal splitter: sidebar | editor+bottom | chat
        self.h_split = QSplitter(Qt.Orientation.Horizontal)
        self.h_split.setHandleWidth(1)

        # Sidebar
        self.file_explorer = FileExplorer()
        self.file_explorer.setMinimumWidth(150)
        self.file_explorer.setMaximumWidth(500)
        self.h_split.addWidget(self.file_explorer)

        # Center column: breadcrumb + editor + bottom panel
        center = QWidget()
        center_lay = QVBoxLayout(center)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(0)

        self.breadcrumb = BreadcrumbBar()
        center_lay.addWidget(self.breadcrumb)

        # Vertical splitter: editor | bottom panel
        self.v_split = QSplitter(Qt.Orientation.Vertical)
        self.v_split.setHandleWidth(1)

        self.tab_manager = TabManager()
        self.v_split.addWidget(self.tab_manager)

        # Bottom panel (tabbed: Terminal, Problems, Output)
        self.bottom_panel = QTabWidget()
        self.bottom_panel.setObjectName("bottomPanel")
        self.bottom_panel.setTabsClosable(False)
        self.bottom_panel.setMovable(False)
        self.bottom_panel.setMinimumHeight(80)
        self.bottom_panel.setMaximumHeight(500)

        self.terminal = TerminalPanel()
        self.bottom_panel.addTab(self.terminal, "TERMINAL")

        # Problems / Output tabs (placeholder)
        problems = QLabel("  No problems detected.")
        problems.setStyleSheet(f"color: {get_theme()['fg_dim']}; padding: 12px; background: {get_theme()['bg_panel']};")
        self.bottom_panel.addTab(problems, "PROBLEMS")

        output_log = QLabel("  Output will appear here.")
        output_log.setStyleSheet(problems.styleSheet())
        self.bottom_panel.addTab(output_log, "OUTPUT")

        self.v_split.addWidget(self.bottom_panel)
        self.v_split.setSizes([620, 220])
        center_lay.addWidget(self.v_split)
        self.h_split.addWidget(center)

        # Chat panel (hidden by default)
        self.chat_panel = ChatPanel()
        self.chat_panel.setMinimumWidth(260)
        self.chat_panel.setMaximumWidth(520)
        self.h_split.addWidget(self.chat_panel)

        self.h_split.setSizes([240, 960, 0])

        main_lay.addWidget(self.h_split)
        root.addWidget(main_area)

        # Wire activity bar buttons
        t = get_theme()
        self.activity_bar._buttons["explorer"].clicked.connect(self._toggle_sidebar)
        self.activity_bar._buttons["search"].clicked.connect(self._find)
        self.activity_bar._buttons["run"].clicked.connect(self._run_file)

    # ── Status Bar ──────────────────────────────────────────────
    def _setup_statusbar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)

        def slbl(text="", hover=True):
            lbl = QLabel(text)
            t = get_theme()
            style = f"""
                QLabel {{
                    background: transparent;
                    color: {t['statusbar_fg']};
                    font-size: 12px;
                    padding: 0 8px;
                    min-height: 22px;
                    font-family: "Segoe UI", system-ui, sans-serif;
                }}
            """
            if hover:
                style += f"QLabel:hover {{ background: rgba(255,255,255,0.12); }}"
            lbl.setStyleSheet(style)
            return lbl

        # Left side
        self.sb_branch = slbl("  main")
        sb.addWidget(self.sb_branch)

        # Right side (permanent = right-aligned)
        self.sb_errors = slbl("⓪ 0  ⚠ 0")
        self.sb_sel = slbl("")
        self.sb_pos = slbl("Ln 1, Col 1")
        self.sb_indent = slbl("Spaces: 4")
        self.sb_enc = slbl("UTF-8")
        self.sb_eol = slbl("LF")
        self.sb_lang = slbl("Plain Text")
        self.sb_msg = slbl("", hover=False)

        for w in [self.sb_errors, self.sb_msg, self.sb_sel, self.sb_lang,
                  self.sb_indent, self.sb_enc, self.sb_eol, self.sb_pos]:
            sb.addPermanentWidget(w)

        self._msg_timer = QTimer()
        self._msg_timer.setSingleShot(True)
        self._msg_timer.timeout.connect(lambda: self.sb_msg.setText(""))

    def _flash(self, msg, ms=3000):
        self.sb_msg.setText(f"  {msg}  ")
        self._msg_timer.start(ms)

    # ── Signals ─────────────────────────────────────────────────
    def _connect_signals(self):
        self.file_explorer.file_opened.connect(self._open_path)
        self.tab_manager.active_editor_changed.connect(self._on_editor_changed)
        self.tab_manager.stats_changed.connect(self._update_stats)
        self.tab_manager.title_changed.connect(self._on_title_changed)
        self.chat_panel.insert_code.connect(self._inject_code)

    def _on_title_changed(self, name):
        self.setWindowTitle(f"{name} — Volt")
        tab = self.tab_manager.current_tab()
        if tab and tab.file_path:
            self.breadcrumb.set_path(tab.file_path)
        else:
            self.breadcrumb.set_path(name)

    def _on_editor_changed(self, editor):
        fb = self.tab_manager.find_bar()
        if fb: fb.set_editor(editor)
        self._update_stats()
        tab = self.tab_manager.current_tab()
        if tab and tab.file_path:
            self.breadcrumb.set_path(tab.file_path)

    def _update_stats(self):
        e = self.tab_manager.current_editor()
        if not e: return
        line, col, lines, chars, sel = e.get_stats()
        self.sb_pos.setText(f"Ln {line}, Col {col}")
        self.sb_sel.setText(f"({sel} selected)" if sel else "")
        fp = e.file_path
        ext = os.path.splitext(fp)[1].lower() if fp else ""
        lang_map = {
            ".py":"Python", ".js":"JavaScript", ".ts":"TypeScript",
            ".jsx":"React JSX", ".tsx":"React TSX", ".html":"HTML",
            ".css":"CSS", ".scss":"SCSS", ".json":"JSON",
            ".md":"Markdown", ".sh":"Shell", ".cpp":"C++",
            ".c":"C", ".h":"C/C++ Header", ".sql":"SQL",
            ".yaml":"YAML", ".yml":"YAML", ".xml":"XML",
        }
        self.sb_lang.setText(lang_map.get(ext, ext[1:].upper() if ext else "Plain Text"))

    # ── File actions ────────────────────────────────────────────
    def _new_file(self):  self.tab_manager.new_tab()

    def _open_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Open File", "",
            "All Files (*);;Python (*.py);;JavaScript (*.js);;TypeScript (*.ts);;"
            "HTML (*.html);;CSS (*.css);;JSON (*.json);;Markdown (*.md)")
        for p in paths: self._open_path(p)

    def _open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if path:
            self.file_explorer.set_root(path)
            self.terminal.set_cwd(path)
            self.setWindowTitle(f"{os.path.basename(path)} — Volt")

    def _open_path(self, path):
        self.tab_manager.open_file(path)
        self.terminal.set_cwd(os.path.dirname(path))
        self.breadcrumb.set_path(path)

    def _save(self):
        self.tab_manager.save_current()
        self._flash("Saved")

    def _save_as(self):    self.tab_manager.save_current_as()
    def _save_all(self):   self.tab_manager.save_all(); self._flash("All files saved")
    def _close_tab(self):  self.tab_manager.close_current()

    # ── Edit actions ────────────────────────────────────────────
    def _editor(self): return self.tab_manager.current_editor()
    def _undo(self):
        e = self._editor()
        if e: e.undo()
    def _redo(self):
        e = self._editor()
        if e: e.redo()
    def _cut(self):
        e = self._editor()
        if e: e.cut()
    def _copy(self):
        e = self._editor()
        if e: e.copy()
    def _paste(self):
        e = self._editor()
        if e: e.paste()
    def _select_all(self):
        e = self._editor()
        if e: e.selectAll()
    def _toggle_comment(self):
        e = self._editor()
        if e: e.toggle_comment()
    def _duplicate_line(self):
        e = self._editor()
        if e: e.duplicate_line()
    def _move_line_up(self):
        e = self._editor()
        if e: e.move_line_up()
    def _move_line_down(self):
        e = self._editor()
        if e: e.move_line_down()
    def _indent(self):
        e = self._editor()
        if e: e.indent_selection()
    def _unindent(self):
        e = self._editor()
        if e: e.unindent_selection()

    def _find(self):
        fb = self.tab_manager.find_bar()
        if fb:
            e = self._editor()
            fb.open_find(e.selectedText() if e else "")

    def _replace(self):
        fb = self.tab_manager.find_bar()
        if fb:
            e = self._editor()
            fb.open_replace(e.selectedText() if e else "")

    def _goto_line(self):
        e = self._editor()
        if not e: return
        line, ok = QInputDialog.getInt(self, "Go to Line", f"Line (1–{e.lines()}):", 1, 1, e.lines())
        if ok: e.goto_line(line)

    def _format_document(self):
        e = self._editor()
        if not e or not e.file_path:
            self._flash("Save file first to format")
            return
        ext = os.path.splitext(e.file_path)[1].lower()
        cmds = {".py": f"black {e.file_path}",
                ".js": f"prettier --write {e.file_path}",
                ".ts": f"prettier --write {e.file_path}",
                ".jsx": f"prettier --write {e.file_path}",
                ".tsx": f"prettier --write {e.file_path}",
                ".json": f"prettier --write {e.file_path}",
                ".css": f"prettier --write {e.file_path}",
                ".html": f"prettier --write {e.file_path}"}
        cmd = cmds.get(ext)
        if cmd:
            self._save()
            self.terminal.run_command(cmd)
            QTimer.singleShot(1500, lambda: self._reload(e.file_path, e))
        else:
            self._flash(f"No formatter for {ext}")

    def _reload(self, path, editor):
        try:
            with open(path, encoding="utf-8") as f:
                editor.setText(f.read())
            editor.mark_saved()
            self._flash("Formatted")
        except Exception: pass

    # ── View actions ────────────────────────────────────────────
    def _toggle_sidebar(self):
        self.file_explorer.setVisible(not self.file_explorer.isVisible())

    def _toggle_terminal(self):
        visible = self.bottom_panel.isVisible()
        self.bottom_panel.setVisible(not visible)
        if not visible:
            self.bottom_panel.setCurrentIndex(0)

    def _toggle_chat(self):
        sizes = self.h_split.sizes()
        if sizes[2] < 50:
            self.h_split.setSizes([sizes[0], max(200, sizes[1] - 320), 320])
        else:
            self.h_split.setSizes([sizes[0], sizes[1] + sizes[2], 0])

    def _toggle_zen(self):
        self._zen_mode = not self._zen_mode
        if self._zen_mode:
            self._prev_sidebar = self.file_explorer.isVisible()
            self._prev_bottom = self.bottom_panel.isVisible()
            self.file_explorer.hide()
            self.bottom_panel.hide()
            self.activity_bar.hide()
            self.toolbar.hide()
            self.menuBar().hide()
            self.statusBar().hide()
            self.breadcrumb.hide()
            self.showFullScreen()
        else:
            self.file_explorer.setVisible(self._prev_sidebar)
            self.bottom_panel.setVisible(self._prev_bottom)
            self.activity_bar.show()
            self.toolbar.show()
            self.menuBar().show()
            self.statusBar().show()
            self.breadcrumb.show()
            self.showNormal()

    def _zoom_in(self):
        e = self._editor()
        if e: e.zoomIn(1)
    def _zoom_out(self):
        e = self._editor()
        if e: e.zoomOut(1)
    def _zoom_reset(self):
        e = self._editor()
        if e: e.zoomTo(0)

    def _change_theme(self, name):
        set_theme(name)
        self._apply_theme()
        self.tab_manager.refresh_all_themes()
        self._flash(f"Theme: {THEMES[name]['name']}")

    # ── Run ─────────────────────────────────────────────────────
    def _run_file(self):
        self._save()
        e = self._editor()
        if not e or not e.file_path:
            self._flash("Save file first")
            return
        ext = os.path.splitext(e.file_path)[1].lower()
        runners = {
            ".py": f'python3 "{e.file_path}"',
            ".js": f'node "{e.file_path}"',
            ".ts": f'ts-node "{e.file_path}"',
            ".sh": f'bash "{e.file_path}"',
            ".rb": f'ruby "{e.file_path}"',
            ".php": f'php "{e.file_path}"',
            ".go": f'go run "{e.file_path}"',
        }
        cmd = runners.get(ext, f"echo 'No runner for {ext}'")
        self.bottom_panel.setVisible(True)
        self.bottom_panel.setCurrentIndex(0)
        self.terminal.run_command(cmd)

    def _new_terminal(self):
        self.bottom_panel.setVisible(True)
        self.bottom_panel.setCurrentIndex(0)
        self.terminal.new_terminal()

    # ── Chat ────────────────────────────────────────────────────
    def _inject_code(self, _):
        e = self._editor()
        if e:
            sel = e.selectedText()
            self.chat_panel.inject_code(sel if sel else e.text()[:3000])

    # ── Help ────────────────────────────────────────────────────
    def _show_shortcuts(self):
        t = get_theme()
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setText("""<table style='font-size:13px;font-family:Consolas,monospace;border-collapse:collapse'>
<tr><td colspan=2 style='color:#569cd6;font-weight:bold;padding:8px 0 4px'>File</td></tr>
<tr><td style='padding:3px 24px 3px 0'>Ctrl+N</td><td>New File</td></tr>
<tr><td>Ctrl+O</td><td>Open File</td></tr>
<tr><td>Ctrl+S</td><td>Save</td></tr>
<tr><td>Ctrl+W</td><td>Close Tab</td></tr>
<tr><td colspan=2 style='color:#569cd6;font-weight:bold;padding:8px 0 4px'>Edit</td></tr>
<tr><td>Ctrl+Z / Ctrl+Shift+Z</td><td>Undo / Redo</td></tr>
<tr><td>Ctrl+F</td><td>Find</td></tr>
<tr><td>Ctrl+H</td><td>Replace</td></tr>
<tr><td>Ctrl+G</td><td>Go to Line</td></tr>
<tr><td>Ctrl+/</td><td>Toggle Comment</td></tr>
<tr><td>Ctrl+D</td><td>Duplicate Line</td></tr>
<tr><td>Alt+↑/↓</td><td>Move Line</td></tr>
<tr><td>Shift+Alt+F</td><td>Format Document</td></tr>
<tr><td colspan=2 style='color:#569cd6;font-weight:bold;padding:8px 0 4px'>View</td></tr>
<tr><td>Ctrl+B</td><td>Toggle Sidebar</td></tr>
<tr><td>Ctrl+`</td><td>Toggle Terminal</td></tr>
<tr><td>Ctrl+Shift+A</td><td>Toggle AI Chat</td></tr>
<tr><td>F11</td><td>Zen Mode</td></tr>
<tr><td>Ctrl+= / Ctrl+-</td><td>Zoom In/Out</td></tr>
<tr><td colspan=2 style='color:#569cd6;font-weight:bold;padding:8px 0 4px'>Run</td></tr>
<tr><td>F5</td><td>Run File</td></tr>
<tr><td>Ctrl+Shift+`</td><td>New Terminal</td></tr>
</table>""")
        msg.exec()

    def _about(self):
        QMessageBox.about(self, "About Volt",
            "<b>⚡ Volt Code Editor v1.0</b><br><br>"
            "A VS Code-style professional code editor built with PyQt6 + QScintilla.<br><br>"
            "Syntax highlighting · File explorer · Multi-tab · Integrated terminal<br>"
            "Find &amp; Replace · Code folding · AI agent chat · 3 themes")

    # ── Close ───────────────────────────────────────────────────
    def closeEvent(self, event):
        from editor.tab_manager import EditorTab
        modified = [
            self.tab_manager.tabs.tabs.widget(i)
            for i in range(self.tab_manager.tabs.tabs.count())
            if isinstance(self.tab_manager.tabs.tabs.widget(i), EditorTab)
            and self.tab_manager.tabs.tabs.widget(i).is_modified
        ]
        if modified:
            r = QMessageBox.question(self, "Unsaved Changes",
                f"{len(modified)} unsaved file(s). Save all?",
                QMessageBox.StandardButton.SaveAll |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel:
                event.ignore(); return
            elif r == QMessageBox.StandardButton.SaveAll:
                self.tab_manager.save_all()
        event.accept()
