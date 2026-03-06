"""Theme definitions for Volt Editor."""

THEMES = {
    "dark": {
        "name": "Volt Dark",
        # App-wide
        "bg":           "#0a0b10",
        "bg2":          "#0f111a",
        "bg3":          "#161925",
        "bg4":          "#1f2335",
        "border":       "#24283b",
        "accent":       "#7aa2f7",
        "accent2":      "#bb9af7",
        "accent3":      "#7dcfff",
        "green":        "#9ece6a",
        "orange":       "#ff9e64",
        "red":          "#f7768e",
        "yellow":       "#e0af68",
        "text":         "#c0caf5",
        "text2":        "#9aa5ce",
        "text3":        "#565f89",
        "selection":    "#33467c",
        "tab_active":   "#161925",
        "tab_inactive": "#0f111a",
        # Editor (QScintilla lexer colours)
        "ed_bg":        "#0a0b10",
        "ed_fg":        "#c0caf5",
        "ed_caret":     "#bb9af7",
        "ed_margin_bg": "#0f111a",
        "ed_margin_fg": "#565f89",
        "ed_sel":       "#33467c",
        "ed_fold":      "#1f2335",
        # Syntax
        "syn_keyword":  "#bb9af7",
        "syn_string":   "#9ece6a",
        "syn_comment":  "#565f89",
        "syn_number":   "#ff9e64",
        "syn_class":    "#7dcfff",
        "syn_func":     "#7aa2f7",
        "syn_operator": "#89ddff",
        "syn_builtin":  "#e0af68",
        "syn_decorator":"#f7768e",
        # Terminal
        "term_bg":      "#06070a",
        "term_fg":      "#9ece6a",
        # Chat
        "chat_user_bg": "#1f2335",
        "chat_ai_bg":   "#161925",
        "chat_input_bg":"#0f111a",
    },
    "light": {
        "name": "Light",
        "bg":           "#f8f9fc",
        "bg2":          "#ffffff",
        "bg3":          "#f1f3f9",
        "bg4":          "#e5e9f5",
        "border":       "#d1d8e8",
        "accent":       "#6d55ff",
        "accent2":      "#7c6aff",
        "accent3":      "#0ea5e9",
        "green":        "#059669",
        "orange":       "#ea580c",
        "red":          "#dc2626",
        "yellow":       "#d97706",
        "text":         "#1e2340",
        "text2":        "#4a5578",
        "text3":        "#94a3b8",
        "selection":    "#c7d2fe",
        "tab_active":   "#ffffff",
        "tab_inactive": "#f1f3f9",
        "ed_bg":        "#ffffff",
        "ed_fg":        "#1e2340",
        "ed_caret":     "#6d55ff",
        "ed_margin_bg": "#f1f3f9",
        "ed_margin_fg": "#94a3b8",
        "ed_sel":       "#c7d2fe",
        "ed_fold":      "#e5e9f5",
        "syn_keyword":  "#6d55ff",
        "syn_string":   "#059669",
        "syn_comment":  "#94a3b8",
        "syn_number":   "#ea580c",
        "syn_class":    "#0ea5e9",
        "syn_func":     "#6d55ff",
        "syn_operator": "#dc2626",
        "syn_builtin":  "#d97706",
        "syn_decorator":"#db2777",
        "term_bg":      "#1e2340",
        "term_fg":      "#34d399",
        "chat_user_bg": "#e5e9f5",
        "chat_ai_bg":   "#f1f3f9",
        "chat_input_bg":"#ffffff",
    },
    "monokai": {
        "name": "Monokai",
        "bg":           "#272822",
        "bg2":          "#1e1f1c",
        "bg3":          "#2d2e27",
        "bg4":          "#383a30",
        "border":       "#404035",
        "accent":       "#a6e22e",
        "accent2":      "#e6db74",
        "accent3":      "#66d9e8",
        "green":        "#a6e22e",
        "orange":       "#fd971f",
        "red":          "#f92672",
        "yellow":       "#e6db74",
        "text":         "#f8f8f2",
        "text2":        "#75715e",
        "text3":        "#49483e",
        "selection":    "#49483e",
        "tab_active":   "#272822",
        "tab_inactive": "#1e1f1c",
        "ed_bg":        "#272822",
        "ed_fg":        "#f8f8f2",
        "ed_caret":     "#f8f8f0",
        "ed_margin_bg": "#1e1f1c",
        "ed_margin_fg": "#49483e",
        "ed_sel":       "#49483e",
        "ed_fold":      "#383a30",
        "syn_keyword":  "#f92672",
        "syn_string":   "#e6db74",
        "syn_comment":  "#75715e",
        "syn_number":   "#ae81ff",
        "syn_class":    "#a6e22e",
        "syn_func":     "#a6e22e",
        "syn_operator": "#f92672",
        "syn_builtin":  "#66d9e8",
        "syn_decorator":"#a6e22e",
        "term_bg":      "#1e1f1c",
        "term_fg":      "#a6e22e",
        "chat_user_bg": "#383a30",
        "chat_ai_bg":   "#2d2e27",
        "chat_input_bg":"#1e1f1c",
    },
    "sunset": {
        "name": "Sunset Gold",
        "bg":           "#1a1412",
        "bg2":          "#211a18",
        "bg3":          "#2d2320",
        "bg4":          "#3a2d29",
        "border":       "#4a3934",
        "accent":       "#f59e0b",
        "accent2":      "#fbbf24",
        "accent3":      "#fcd34d",
        "green":        "#10b981",
        "orange":       "#f97316",
        "red":          "#ef4444",
        "yellow":       "#fbbf24",
        "text":         "#fff7ed",
        "text2":        "#fed7aa",
        "text3":        "#7c2d12",
        "selection":    "#5c2b06",
        "tab_active":   "#2d2320",
        "tab_inactive": "#211a18",
        "ed_bg":        "#1a1412",
        "ed_fg":        "#fff7ed",
        "ed_caret":     "#f59e0b",
        "ed_margin_bg": "#211a18",
        "ed_margin_fg": "#7c2d12",
        "ed_sel":       "#5c2b06",
        "ed_fold":      "#3a2d29",
        "syn_keyword":  "#f97316",
        "syn_string":   "#10b981",
        "syn_comment":  "#7c2d12",
        "syn_number":   "#f59e0b",
        "syn_class":    "#fbbf24",
        "syn_func":     "#ffedd5",
        "syn_operator": "#fcd34d",
        "syn_builtin":  "#f59e0b",
        "syn_decorator":"#f97316",
        "term_bg":      "#120e0c",
        "term_fg":      "#f59e0b",
        "chat_user_bg": "#3a2d29",
        "chat_ai_bg":   "#2d2320",
        "chat_input_bg":"#211a18",
    }
}

CURRENT_THEME = "dark"

def get_theme():
    return THEMES[CURRENT_THEME]

def set_theme(name):
    global CURRENT_THEME
    if name in THEMES:
        CURRENT_THEME = name

def build_stylesheet(t):
    return f"""
QWidget {{
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 13px;
    color: {t['text']};
    background: {t['bg']};
}}
QMainWindow {{
    background: {t['bg']};
}}
/* ─── Toolbar ─── */
QToolBar {{
    background: {t['bg2']};
    border-bottom: 1px solid {t['border']};
    padding: 4px 8px;
    spacing: 4px;
}}
QToolBar QToolButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 5px 10px;
    color: {t['text2']};
    font-size: 12px;
}}
QToolBar QToolButton:hover {{
    background: {t['bg4']};
    color: {t['text']};
}}
QToolBar QToolButton:pressed {{
    background: {t['accent']};
    color: #fff;
}}
QToolBar QComboBox {{
    background: {t['bg3']};
    border: 1px solid {t['border']};
    border-radius: 5px;
    padding: 3px 8px;
    color: {t['text2']};
    min-width: 80px;
}}
QToolBar QComboBox::drop-down {{ border: none; }}
QToolBar QComboBox QAbstractItemView {{
    background: {t['bg3']};
    border: 1px solid {t['border']};
    color: {t['text']};
    selection-background-color: {t['accent']};
}}
/* ─── Menu ─── */
QMenuBar {{
    background: {t['bg2']};
    border-bottom: 1px solid {t['border']};
    padding: 2px;
    color: {t['text']};
}}
QMenuBar::item:selected {{ background: {t['bg4']}; border-radius: 4px; }}
QMenu {{
    background: {t['bg3']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    padding: 4px;
    color: {t['text']};
}}
QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {t['accent']}; color: #fff; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
/* ─── Tab Bar ─── */
QTabWidget::pane {{
    border: none;
    background: {t['tab_active']};
}}
QTabBar {{
    background: {t['bg2']};
}}
QTabBar::tab {{
    background: {t['tab_inactive']};
    color: {t['text2']};
    border: none;
    border-right: 1px solid {t['border']};
    padding: 6px 16px;
    min-width: 120px;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {t['tab_active']};
    color: {t['text']};
    border-bottom: 2px solid {t['accent']};
}}
QTabBar::tab:hover:!selected {{
    background: {t['bg3']};
    color: {t['text']};
}}
QTabBar::close-button {{
    image: url(no_image); /* Hide default */
    subcontrol-position: right;
    width: 16px; height: 16px;
}}
QTabBar::close-button:hover {{
    background: {t['red']};
    border-radius: 8px;
}}
/* ─── Splitter ─── */
QSplitter::handle {{
    background: {t['border']};
    width: 1px;
    height: 1px;
}}
/* ─── Sidebar / Tree ─── */
QTreeView {{
    background: {t['bg2']};
    border: none;
    color: {t['text2']};
    font-size: 12px;
    outline: none;
}}
QTreeView::item {{ padding: 3px 4px; border-radius: 4px; }}
QTreeView::item:selected {{
    background: {t['bg4']};
    color: {t['text']};
}}
QTreeView::item:hover:!selected {{
    background: {t['bg3']};
}}
QTreeView::branch {{ background: {t['bg2']}; }}
/* ─── Scrollbars ─── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {t['border']};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {t['text3']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {t['border']};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{ background: {t['text3']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
/* ─── Status Bar ─── */
QStatusBar {{
    background: {t['bg2']};
    border-top: 1px solid {t['border']};
    color: {t['text2']};
    font-size: 11px;
    padding: 0 8px;
}}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{
    color: rgba(255,255,255,0.85);
    font-size: 11px;
    padding: 0 8px;
}}
/* ─── Find Bar ─── */
QLineEdit {{
    background: {t['bg3']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 5px 10px;
    color: {t['text']};
    selection-background-color: {t['accent']};
}}
QLineEdit:focus {{
    border-color: {t['accent']};
}}
QPushButton {{
    background: {t['bg4']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 5px 14px;
    color: {t['text']};
    font-size: 12px;
}}
QPushButton:hover {{
    background: {t['accent']};
    border-color: {t['accent']};
    color: #fff;
}}
QPushButton:pressed {{ opacity: 0.8; }}
QPushButton#accent {{
    background: {t['accent']};
    border-color: {t['accent']};
    color: #fff;
    font-weight: 600;
}}
QPushButton#accent:hover {{
    background: {t['accent2']};
}}
/* ─── Terminal ─── */
QPlainTextEdit#terminal {{
    background: {t['term_bg']};
    color: {t['term_fg']};
    border: none;
    font-size: 12px;
    padding: 8px;
}}
/* ─── Chat ─── */
QScrollArea#chatArea {{
    background: {t['bg']};
    border: none;
}}
QTextEdit#chatInput {{
    background: {t['chat_input_bg']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    color: {t['text']};
    padding: 8px 12px;
    font-size: 13px;
}}
QTextEdit#chatInput:focus {{
    border-color: {t['accent']};
}}
QLabel#chatLabel {{
    color: {t['text2']};
    font-size: 11px;
}}
/* ─── Panel header labels ─── */
QLabel#panelHeader {{
    background: {t['bg2']};
    color: {t['text3']};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    padding: 6px 12px;
    border-bottom: 1px solid {t['border']};
    text-transform: uppercase;
}}
/* ─── Checkboxes, ComboBox ─── */
QCheckBox {{ color: {t['text2']}; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border-radius: 3px;
    border: 1px solid {t['border']};
    background: {t['bg3']};
}}
QCheckBox::indicator:checked {{
    background: {t['accent']};
    border-color: {t['accent']};
}}
"""
