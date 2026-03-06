"""
VS Code / Antigravity-style theme system for Volt Editor.
Pixel-precise, dense, professional — every measurement deliberate.
"""

THEMES = {
    "vscode_dark": {
        "name": "VS Dark",
        "bg":              "#1e1e1e",
        "bg_sidebar":      "#252526",
        "bg_titlebar":     "#3c3c3c",
        "bg_toolbar":      "#333333",
        "bg_tab_active":   "#1e1e1e",
        "bg_tab_inactive": "#2d2d2d",
        "bg_tab_hover":    "#2a2a2a",
        "bg_panel":        "#1e1e1e",
        "bg_input":        "#3c3c3c",
        "bg_dropdown":     "#252526",
        "bg_hover":        "#2a2d2e",
        "bg_selection":    "#094771",
        "bg_highlight":    "#2d2d2d",
        "bg_widget":       "#252526",
        "bg_button":       "#0e639c",
        "bg_button_hover": "#1177bb",
        "bg_badge":        "#4d4d4d",
        "border":          "#474747",
        "border_focus":    "#007fd4",
        "border_input":    "#3c3c3c",
        "border_panel":    "#474747",
        "fg":              "#cccccc",
        "fg_dim":          "#858585",
        "fg_disabled":     "#555555",
        "fg_link":         "#3794ff",
        "fg_white":        "#ffffff",
        "accent":          "#007acc",
        "accent_hover":    "#1a8fd1",
        "accent_green":    "#4ec9b0",
        "accent_yellow":   "#dcdcaa",
        "accent_orange":   "#ce9178",
        "accent_red":      "#f44747",
        "accent_purple":   "#c586c0",
        "accent_blue":     "#9cdcfe",
        "accent_lt_blue":  "#4fc1ff",
        "statusbar_bg":    "#007acc",
        "statusbar_fg":    "#ffffff",
        "actbar_bg":       "#333333",
        "actbar_fg":       "#858585",
        "actbar_fg_active":"#ffffff",
        "actbar_border":   "#2b2b2b",
        "term_bg":         "#1e1e1e",
        "term_fg":         "#cccccc",
        "term_sel":        "#264f78",
        "chat_bg":         "#252526",
        "chat_user_bg":    "#2d2d2d",
        "chat_ai_bg":      "#252526",
        "chat_input_bg":   "#3c3c3c",
        "chat_border":     "#474747",
        "syn_comment":     "#6a9955",
        "syn_string":      "#ce9178",
        "syn_keyword":     "#569cd6",
        "syn_keyword2":    "#c586c0",
        "syn_number":      "#b5cea8",
        "syn_type":        "#4ec9b0",
        "syn_function":    "#dcdcaa",
        "syn_variable":    "#9cdcfe",
        "syn_operator":    "#d4d4d4",
        "syn_decorator":   "#dcdcaa",
        "syn_builtin":     "#4fc1ff",
        "syn_class":       "#4ec9b0",
        "ed_bg":           "#1e1e1e",
        "ed_fg":           "#d4d4d4",
        "ed_caret":        "#aeafad",
        "ed_sel":          "#264f78",
        "ed_line_highlight":"#2d2d2d",
        "ed_margin_bg":    "#1e1e1e",
        "ed_margin_fg":    "#858585",
        "ed_fold":         "#404040",
        "ed_ruler":        "#3b3b3b",
        "ed_indent_guide": "#404040",
    },
    "vscode_light": {
        "name": "VS Light",
        "bg":              "#ffffff",
        "bg_sidebar":      "#f3f3f3",
        "bg_titlebar":     "#dddddd",
        "bg_toolbar":      "#f3f3f3",
        "bg_tab_active":   "#ffffff",
        "bg_tab_inactive": "#ececec",
        "bg_tab_hover":    "#f0f0f0",
        "bg_panel":        "#f3f3f3",
        "bg_input":        "#ffffff",
        "bg_dropdown":     "#f3f3f3",
        "bg_hover":        "#e8e8e8",
        "bg_selection":    "#add6ff",
        "bg_highlight":    "#f0f0f0",
        "bg_widget":       "#f3f3f3",
        "bg_button":       "#007acc",
        "bg_button_hover": "#0062a3",
        "bg_badge":        "#c4c4c4",
        "border":          "#d4d4d4",
        "border_focus":    "#0090f1",
        "border_input":    "#cecece",
        "border_panel":    "#d4d4d4",
        "fg":              "#383838",
        "fg_dim":          "#717171",
        "fg_disabled":     "#aaaaaa",
        "fg_link":         "#006ab1",
        "fg_white":        "#ffffff",
        "accent":          "#007acc",
        "accent_hover":    "#005fa3",
        "accent_green":    "#267f99",
        "accent_yellow":   "#795e26",
        "accent_orange":   "#a31515",
        "accent_red":      "#cd3131",
        "accent_purple":   "#af00db",
        "accent_blue":     "#001080",
        "accent_lt_blue":  "#0070c1",
        "statusbar_bg":    "#007acc",
        "statusbar_fg":    "#ffffff",
        "actbar_bg":       "#2c2c2c",
        "actbar_fg":       "#858585",
        "actbar_fg_active":"#ffffff",
        "actbar_border":   "#252525",
        "term_bg":         "#ffffff",
        "term_fg":         "#000000",
        "term_sel":        "#add6ff",
        "chat_bg":         "#f3f3f3",
        "chat_user_bg":    "#e8e8e8",
        "chat_ai_bg":      "#f3f3f3",
        "chat_input_bg":   "#ffffff",
        "chat_border":     "#d4d4d4",
        "syn_comment":     "#008000",
        "syn_string":      "#a31515",
        "syn_keyword":     "#0000ff",
        "syn_keyword2":    "#af00db",
        "syn_number":      "#098658",
        "syn_type":        "#267f99",
        "syn_function":    "#795e26",
        "syn_variable":    "#001080",
        "syn_operator":    "#383838",
        "syn_decorator":   "#795e26",
        "syn_builtin":     "#0070c1",
        "syn_class":       "#267f99",
        "ed_bg":           "#ffffff",
        "ed_fg":           "#000000",
        "ed_caret":        "#000000",
        "ed_sel":          "#add6ff",
        "ed_line_highlight":"#f0f0f0",
        "ed_margin_bg":    "#f3f3f3",
        "ed_margin_fg":    "#999999",
        "ed_fold":         "#d4d4d4",
        "ed_ruler":        "#d3d3d3",
        "ed_indent_guide": "#d4d4d4",
    },
    "monokai_pro": {
        "name": "Monokai Pro",
        "bg":              "#2d2a2e",
        "bg_sidebar":      "#221f22",
        "bg_titlebar":     "#1a1a1a",
        "bg_toolbar":      "#221f22",
        "bg_tab_active":   "#2d2a2e",
        "bg_tab_inactive": "#221f22",
        "bg_tab_hover":    "#2d2a2e",
        "bg_panel":        "#221f22",
        "bg_input":        "#3a3a3c",
        "bg_dropdown":     "#221f22",
        "bg_hover":        "#393b3d",
        "bg_selection":    "#5b595c",
        "bg_highlight":    "#3a3a3c",
        "bg_widget":       "#221f22",
        "bg_button":       "#727072",
        "bg_button_hover": "#939293",
        "bg_badge":        "#4d4d4d",
        "border":          "#474747",
        "border_focus":    "#a9dc76",
        "border_input":    "#474747",
        "border_panel":    "#474747",
        "fg":              "#fcfcfa",
        "fg_dim":          "#939293",
        "fg_disabled":     "#5b595c",
        "fg_link":         "#78dce8",
        "fg_white":        "#ffffff",
        "accent":          "#a9dc76",
        "accent_hover":    "#97cb64",
        "accent_green":    "#a9dc76",
        "accent_yellow":   "#ffd866",
        "accent_orange":   "#fc9867",
        "accent_red":      "#ff6188",
        "accent_purple":   "#ab9df2",
        "accent_blue":     "#78dce8",
        "accent_lt_blue":  "#78dce8",
        "statusbar_bg":    "#221f22",
        "statusbar_fg":    "#939293",
        "actbar_bg":       "#221f22",
        "actbar_fg":       "#939293",
        "actbar_fg_active":"#fcfcfa",
        "actbar_border":   "#1a1a1a",
        "term_bg":         "#221f22",
        "term_fg":         "#fcfcfa",
        "term_sel":        "#5b595c",
        "chat_bg":         "#221f22",
        "chat_user_bg":    "#3a3a3c",
        "chat_ai_bg":      "#2d2a2e",
        "chat_input_bg":   "#3a3a3c",
        "chat_border":     "#474747",
        "syn_comment":     "#727072",
        "syn_string":      "#ffd866",
        "syn_keyword":     "#ff6188",
        "syn_keyword2":    "#ab9df2",
        "syn_number":      "#ab9df2",
        "syn_type":        "#78dce8",
        "syn_function":    "#a9dc76",
        "syn_variable":    "#fcfcfa",
        "syn_operator":    "#ff6188",
        "syn_decorator":   "#a9dc76",
        "syn_builtin":     "#78dce8",
        "syn_class":       "#78dce8",
        "ed_bg":           "#2d2a2e",
        "ed_fg":           "#fcfcfa",
        "ed_caret":        "#fcfcfa",
        "ed_sel":          "#5b595c",
        "ed_line_highlight":"#3a3a3c",
        "ed_margin_bg":    "#2d2a2e",
        "ed_margin_fg":    "#5b595c",
        "ed_fold":         "#5b595c",
        "ed_ruler":        "#474747",
        "ed_indent_guide": "#474747",
    },
}

# Add compatibility aliases for older modules
for theme_key in THEMES:
    t = THEMES[theme_key]
    t['bg2'] = t.get('bg_sidebar', t['bg'])
    t['bg3'] = t.get('bg_toolbar', t['bg'])
    t['bg4'] = t.get('bg_input', t['bg'])
    t['text'] = t.get('fg', '#ccc')
    t['text2'] = t.get('fg_dim', '#888')
    t['text3'] = t.get('fg_disabled', '#555')
    t['accent2'] = t.get('accent_hover', t['accent'])
    t['accent3'] = t.get('accent_blue', t['accent'])
    t['green'] = t.get('accent_green', '#4ec9b0')
    t['orange'] = t.get('accent_orange', '#ce9178')
    t['red'] = t.get('accent_red', '#f44747')
    t['yellow'] = t.get('accent_yellow', '#dcdcaa')

CURRENT_THEME = "vscode_dark"

def get_theme():
    return THEMES[CURRENT_THEME]

def set_theme(name):
    global CURRENT_THEME
    if name in THEMES:
        CURRENT_THEME = name

def build_stylesheet(t):
    return f"""
* {{
    font-family: "Segoe UI", "SF Pro Text", system-ui, sans-serif;
    font-size: 13px;
    outline: none;
}}
QWidget {{
    background: {t['bg']};
    color: {t['fg']};
}}
QMainWindow {{ background: {t['bg']}; }}

/* Menu */
QMenuBar {{
    background: {t['bg_toolbar']};
    color: {t['fg']};
    font-size: 12px;
    border-bottom: 1px solid {t['border']};
    padding: 0;
    spacing: 0;
}}
QMenuBar::item {{ background: transparent; padding: 5px 10px; }}
QMenuBar::item:selected {{ background: {t['bg_hover']}; }}
QMenuBar::item:pressed {{ background: {t['bg_selection']}; }}
QMenu {{
    background: {t['bg_dropdown']};
    border: 1px solid {t['border']};
    padding: 2px 0;
    font-size: 13px;
}}
QMenu::item {{ padding: 5px 32px 5px 12px; color: {t['fg']}; background: transparent; }}
QMenu::item:selected {{ background: {t['accent']}; color: {t['fg_white']}; }}
QMenu::item:disabled {{ color: {t['fg_disabled']}; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 2px 0; }}

/* Toolbar */
QToolBar {{
    background: {t['bg_toolbar']};
    border-bottom: 1px solid {t['border']};
    padding: 2px 4px;
    spacing: 1px;
}}
QToolBar::separator {{ width: 1px; background: {t['border']}; margin: 3px 4px; }}
QToolBar QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 3px 5px;
    color: {t['fg']};
    font-size: 13px;
    min-width: 24px; min-height: 24px;
}}
QToolBar QToolButton:hover {{ background: {t['bg_hover']}; }}
QToolBar QToolButton:pressed {{ background: {t['bg_selection']}; }}

/* Tabs */
QTabWidget::pane {{ border: none; background: {t['bg']}; }}
QTabBar {{ background: {t['bg_toolbar']}; }}
QTabBar::tab {{
    background: {t['bg_tab_inactive']};
    color: {t['fg_dim']};
    border: none;
    border-right: 1px solid {t['border']};
    padding: 0 16px 0 12px;
    height: 35px;
    min-width: 80px; max-width: 200px;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background: {t['bg_tab_active']};
    color: {t['fg']};
    border-top: 1px solid {t['accent']};
}}
QTabBar::tab:hover:!selected {{
    background: {t['bg_tab_hover']};
    color: {t['fg']};
}}

/* Splitter */
QSplitter::handle {{ background: {t['border']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QSplitter::handle:hover {{ background: {t['accent']}; }}

/* Tree */
QTreeView {{
    background: {t['bg_sidebar']}; border: none; color: {t['fg']};
    font-size: 13px; outline: none; show-decoration-selected: 1;
}}
QTreeView::item {{ padding: 1px 0; height: 22px; }}
QTreeView::item:selected {{ background: {t['bg_selection']}; color: {t['fg']}; }}
QTreeView::item:hover:!selected {{ background: {t['bg_hover']}; }}
QTreeView::branch {{ background: {t['bg_sidebar']}; }}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t['bg_badge']}; border-radius: 5px;
    min-height: 30px; margin: 0 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {t['fg_dim']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{
    background: transparent; height: 10px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t['bg_badge']}; border-radius: 5px;
    min-width: 30px; margin: 2px 0;
}}
QScrollBar::handle:horizontal:hover {{ background: {t['fg_dim']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* Status bar */
QStatusBar {{
    background: {t['statusbar_bg']}; color: {t['statusbar_fg']};
    font-size: 12px; min-height: 22px; max-height: 22px; padding: 0;
    font-family: "Segoe UI", system-ui, sans-serif;
}}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{
    background: transparent; color: {t['statusbar_fg']};
    font-size: 12px; padding: 0 6px; min-height: 22px;
}}
QStatusBar QLabel:hover {{ background: rgba(255,255,255,0.12); }}

/* Inputs */
QLineEdit {{
    background: {t['bg_input']}; border: 1px solid {t['border_input']};
    border-radius: 2px; padding: 3px 8px; color: {t['fg']};
    font-size: 13px; selection-background-color: {t['accent']};
}}
QLineEdit:focus {{ border-color: {t['border_focus']}; }}
QLineEdit:disabled {{ color: {t['fg_disabled']}; }}

/* Buttons */
QPushButton {{
    background: {t['bg_button']}; border: none; border-radius: 2px;
    padding: 4px 14px; color: {t['fg_white']}; font-size: 13px;
}}
QPushButton:hover {{ background: {t['bg_button_hover']}; }}
QPushButton:disabled {{ background: {t['bg_badge']}; color: {t['fg_disabled']}; }}
QPushButton#flat {{
    background: transparent; color: {t['fg_dim']}; padding: 3px 8px;
    border: none;
}}
QPushButton#flat:hover {{ background: {t['bg_hover']}; color: {t['fg']}; }}
QPushButton#icon_btn {{
    background: transparent; border: none; color: {t['fg_dim']};
    padding: 3px; border-radius: 3px; font-size: 14px;
    min-width: 22px; min-height: 22px; max-width: 22px; max-height: 22px;
}}
QPushButton#icon_btn:hover {{ background: {t['bg_hover']}; color: {t['fg']}; }}

/* ComboBox */
QComboBox {{
    background: {t['bg_input']}; border: 1px solid {t['border_input']};
    border-radius: 2px; padding: 3px 8px; color: {t['fg']};
    font-size: 13px; min-height: 22px;
}}
QComboBox:focus {{ border-color: {t['border_focus']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {t['bg_dropdown']}; border: 1px solid {t['border']};
    color: {t['fg']}; selection-background-color: {t['accent']};
    selection-color: {t['fg_white']}; outline: none; padding: 2px 0;
}}
QComboBox QAbstractItemView::item {{ padding: 4px 12px; min-height: 22px; }}

/* Checkboxes */
QCheckBox {{ color: {t['fg']}; spacing: 6px; font-size: 13px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; border-radius: 2px;
    border: 1px solid {t['border']}; background: {t['bg_input']};
}}
QCheckBox::indicator:checked {{
    background: {t['accent']}; border-color: {t['accent']};
}}

/* Terminal */
QPlainTextEdit#terminal {{
    background: {t['term_bg']}; color: {t['term_fg']}; border: none;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px; padding: 6px 8px;
    selection-background-color: {t['term_sel']};
}}

/* Chat */
QScrollArea#chatArea {{ background: {t['chat_bg']}; border: none; }}
QTextEdit#chatInput {{
    background: {t['chat_input_bg']}; border: 1px solid {t['chat_border']};
    border-radius: 2px; color: {t['fg']}; padding: 6px 10px; font-size: 13px;
}}
QTextEdit#chatInput:focus {{ border-color: {t['border_focus']}; }}

/* Panel header */
QLabel#panelHeader {{
    background: {t['bg_sidebar']}; color: {t['fg_dim']};
    font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
    padding: 8px 12px 6px 20px; text-transform: uppercase;
}}

/* Bottom panel tabs */
QTabWidget#bottomPanel::pane {{ border: none; background: {t['bg_panel']}; }}
QTabWidget#bottomPanel QTabBar {{ background: {t['bg_toolbar']}; border-bottom: 1px solid {t['border']}; }}
QTabWidget#bottomPanel QTabBar::tab {{
    background: transparent; color: {t['fg_dim']}; border: none;
    border-bottom: 2px solid transparent;
    padding: 0 14px; height: 30px;
    font-size: 11px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.8px; min-width: 60px;
}}
QTabWidget#bottomPanel QTabBar::tab:selected {{
    color: {t['fg']}; border-bottom: 2px solid {t['accent']};
}}
QTabWidget#bottomPanel QTabBar::tab:hover:!selected {{
    color: {t['fg']}; background: {t['bg_hover']};
}}

/* Tooltips */
QToolTip {{
    background: {t['bg_dropdown']}; color: {t['fg']};
    border: 1px solid {t['border']}; padding: 4px 8px;
    font-size: 12px; border-radius: 0;
}}

/* Dialogs */
QMessageBox {{ background: {t['bg_sidebar']}; }}
QMessageBox QLabel {{ color: {t['fg']}; background: transparent; }}
QDialog {{ background: {t['bg_sidebar']}; }}
QFormLayout QLabel {{ color: {t['fg_dim']}; font-size: 12px; }}

/* PlainTextEdit generic */
QPlainTextEdit {{
    background: {t['bg']}; color: {t['fg']}; border: none;
    selection-background-color: {t['bg_selection']};
}}
"""
