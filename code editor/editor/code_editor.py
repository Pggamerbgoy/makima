"""
Code editor widget using QScintilla for syntax highlighting,
line numbers, code folding, auto-indent, bracket matching.
"""
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QKeySequence
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.Qsci import (
    QsciScintilla, QsciLexerPython, QsciLexerJavaScript,
    QsciLexerHTML, QsciLexerCSS, QsciLexerCPP, QsciLexerJSON,
    QsciLexerBash, QsciLexerSQL, QsciLexerMarkdown,
    QsciLexerYAML, QsciLexerXML
)
from editor.themes import get_theme

LEXERS = {
    ".py":    QsciLexerPython,
    ".js":    QsciLexerJavaScript,
    ".ts":    QsciLexerJavaScript,
    ".jsx":   QsciLexerJavaScript,
    ".tsx":   QsciLexerJavaScript,
    ".html":  QsciLexerHTML,
    ".htm":   QsciLexerHTML,
    ".css":   QsciLexerCSS,
    ".scss":  QsciLexerCSS,
    ".cpp":   QsciLexerCPP,
    ".c":     QsciLexerCPP,
    ".h":     QsciLexerCPP,
    ".hpp":   QsciLexerCPP,
    ".json":  QsciLexerJSON,
    ".sh":    QsciLexerBash,
    ".bash":  QsciLexerBash,
    ".sql":   QsciLexerSQL,
    ".md":    QsciLexerMarkdown,
    ".yaml":  QsciLexerYAML,
    ".yml":   QsciLexerYAML,
    ".xml":   QsciLexerXML,
}

def color(hex_str):
    return QColor(hex_str)

class CodeEditor(QsciScintilla):
    file_path = None
    is_modified = False
    modified_changed = pyqtSignal(bool)

    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)
        self.file_path = file_path
        self._setup_editor()
        self._apply_theme()
        if file_path:
            self._set_lexer_for_file(file_path)

    def _setup_editor(self):
        t = get_theme()
        # Premium Typography
        font = QFont("JetBrains Mono", 12)
        font.setFixedPitch(True)
        # Fallback to Consolas/Courier if needed
        if not font.exactMatch():
            font = QFont("Consolas", 12)
        self.setFont(font)
        
        # Increase line spacing (Extra ascent and descent)
        self.SendScintilla(QsciScintilla.SCI_SETEXTRAASCENT, 4)
        self.SendScintilla(QsciScintilla.SCI_SETEXTRADESCENT, 4)

        # Line numbers
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "00000")
        self.setMarginsFont(QFont("JetBrains Mono", 11))

        # Folding margin
        self.setMarginType(2, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(2, 14)
        self.setMarginSensitivity(2, True)
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 2)

        # Indentation
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        self.setIndentationGuides(True)

        # Brace matching
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

        # Auto-completion
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(False)

        # Call tips
        self.setCallTipsStyle(QsciScintilla.CallTipsStyle.CallTipsContext)

        # Long line indicator
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(80)

        # Whitespace
        self.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsInvisible)

        # EOL
        self.setEolMode(QsciScintilla.EolMode.EolUnix)
        self.setEolVisibility(False)

        # Wrap
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # Scroll width tracking
        self.setScrollWidthTracking(True)

        # Current line highlight
        self.setCaretLineVisible(True)
        self.setCaretWidth(3) # Slightly thicker caret for focus
        self.SendScintilla(QsciScintilla.SCI_SETCARETSTYLE, QsciScintilla.CARETSTYLE_LINE)

        # Multi-selection
        self.SendScintilla(QsciScintilla.SCI_SETMULTIPLESELECTION, 1)
        self.SendScintilla(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING, 1)

        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self):
        if not self.is_modified:
            self.is_modified = True
            self.modified_changed.emit(True)

    def mark_saved(self):
        self.is_modified = False
        self.modified_changed.emit(False)

    def _apply_theme(self):
        t = get_theme()
        # Background / foreground
        self.setPaper(color(t["ed_bg"]))
        self.setColor(color(t["ed_fg"]))
        # Margins
        self.setMarginsForegroundColor(color(t["ed_margin_fg"]))
        self.setMarginsBackgroundColor(color(t["ed_margin_bg"]))
        # Selection
        self.setSelectionBackgroundColor(color(t["ed_sel"]))
        self.setSelectionForegroundColor(color(t["ed_fg"]))
        # Caret
        self.setCaretForegroundColor(color(t["ed_caret"]))
        self.setCaretLineBackgroundColor(color(t["bg3"]))
        # Edge line
        self.setEdgeColor(color(t["border"]))
        # Indentation guides
        self.setIndentationGuidesBackgroundColor(color(t["bg3"]))
        self.setIndentationGuidesForegroundColor(color(t["border"]))
        # Brace match highlight
        self.setMatchedBraceBackgroundColor(color(t["bg4"]))
        self.setMatchedBraceForegroundColor(color(t["accent2"]))
        self.setUnmatchedBraceBackgroundColor(color(t["red"]))
        # Fold margin
        self.setFoldMarginColors(color(t["bg3"]), color(t["bg2"]))
        # Fold markers (mask unsigned 32-bit to signed 32-bit to prevent overflow in PyQt6)
        accent_rgb = int(color(t["accent"]).rgb())
        if accent_rgb > 0x7FFFFFFF:
            accent_rgb -= 0x100000000
        self.SendScintilla(QsciScintilla.SCI_MARKERSETBACK, QsciScintilla.SC_MARKNUM_FOLDEROPEN, accent_rgb)

    def _set_lexer_for_file(self, path):
        import os
        ext = os.path.splitext(path)[1].lower()
        lexer_cls = LEXERS.get(ext)
        if lexer_cls:
            self._apply_lexer(lexer_cls())
        else:
            self.setLexer(None)

    def _apply_lexer(self, lexer):
        t = get_theme()
        font = QFont("JetBrains Mono", 13)
        font.setFixedPitch(True)
        lexer.setFont(font)
        lexer.setDefaultPaper(color(t["ed_bg"]))
        lexer.setDefaultColor(color(t["ed_fg"]))

        # Python-specific colours
        if isinstance(lexer, QsciLexerPython):
            lexer.setColor(color(t["syn_keyword"]),  QsciLexerPython.Keyword)
            lexer.setColor(color(t["syn_string"]),   QsciLexerPython.SingleQuotedString)
            lexer.setColor(color(t["syn_string"]),   QsciLexerPython.DoubleQuotedString)
            lexer.setColor(color(t["syn_string"]),   QsciLexerPython.TripleSingleQuotedString)
            lexer.setColor(color(t["syn_string"]),   QsciLexerPython.TripleDoubleQuotedString)
            lexer.setColor(color(t["syn_comment"]),  QsciLexerPython.Comment)
            lexer.setColor(color(t["syn_comment"]),  QsciLexerPython.CommentBlock)
            lexer.setColor(color(t["syn_number"]),   QsciLexerPython.Number)
            lexer.setColor(color(t["syn_decorator"]),QsciLexerPython.Decorator)
            lexer.setColor(color(t["syn_class"]),    QsciLexerPython.ClassName)
            lexer.setColor(color(t["syn_func"]),     QsciLexerPython.FunctionMethodName)
            lexer.setColor(color(t["syn_builtin"]),  QsciLexerPython.HighlightedIdentifier)
            lexer.setColor(color(t["syn_operator"]), QsciLexerPython.Operator)
            for style in range(128):
                lexer.setPaper(color(t["ed_bg"]), style)

        elif isinstance(lexer, QsciLexerJavaScript):
            lexer.setColor(color(t["syn_keyword"]),  QsciLexerJavaScript.Keyword)
            lexer.setColor(color(t["syn_string"]),   QsciLexerJavaScript.SingleQuotedString)
            lexer.setColor(color(t["syn_string"]),   QsciLexerJavaScript.DoubleQuotedString)
            lexer.setColor(color(t["syn_comment"]),  QsciLexerJavaScript.CommentLine)
            lexer.setColor(color(t["syn_comment"]),  QsciLexerJavaScript.Comment)
            lexer.setColor(color(t["syn_number"]),   QsciLexerJavaScript.Number)
            for style in range(128):
                lexer.setPaper(color(t["ed_bg"]), style)

        elif isinstance(lexer, QsciLexerCPP):
            lexer.setColor(color(t["syn_keyword"]),  QsciLexerCPP.Keyword)
            lexer.setColor(color(t["syn_string"]),   QsciLexerCPP.SingleQuotedString)
            lexer.setColor(color(t["syn_string"]),   QsciLexerCPP.DoubleQuotedString)
            lexer.setColor(color(t["syn_comment"]),  QsciLexerCPP.CommentLine)
            lexer.setColor(color(t["syn_comment"]),  QsciLexerCPP.Comment)
            lexer.setColor(color(t["syn_number"]),   QsciLexerCPP.Number)
            lexer.setColor(color(t["syn_builtin"]),  QsciLexerCPP.PreProcessor)
            for style in range(128):
                lexer.setPaper(color(t["ed_bg"]), style)

        else:
            # Generic colouring for all other lexers
            for style in range(128):
                lexer.setPaper(color(t["ed_bg"]), style)
                lexer.setColor(color(t["ed_fg"]), style)

        self.setLexer(lexer)

    def refresh_theme(self):
        self._apply_theme()
        if self.lexer():
            self._apply_lexer(self.lexer().__class__())

    # ─── Helpers ───────────────────────────────────────────────
    def goto_line(self, line):
        self.setCursorPosition(line - 1, 0)
        self.ensureCursorVisible()
        self.setFocus()

    def find_text(self, text, case=False, whole=False, regex=False, forward=True):
        return self.findFirst(text, regex, case, whole, True, forward)

    def replace_text(self, find, replace, case=False, whole=False, regex=False):
        if self.findFirst(find, regex, case, whole, True):
            self.replace(replace)
            return True
        return False

    def replace_all(self, find, replace, case=False, whole=False, regex=False):
        count = 0
        self.beginUndoAction()
        if self.findFirst(find, regex, case, whole, True):
            self.replace(replace)
            count += 1
            while self.findNext():
                self.replace(replace)
                count += 1
        self.endUndoAction()
        return count

    def toggle_comment(self):
        """Toggle line comment for selected lines."""
        if self.hasSelectedText():
            start_line, _, end_line, _ = self.getSelection()
        else:
            start_line = self.getCursorPosition()[0]
            end_line = start_line

        lexer = self.lexer()
        comment = "#"
        if isinstance(lexer, (QsciLexerJavaScript, QsciLexerCPP, QsciLexerCSS)):
            comment = "//"
        elif isinstance(lexer, QsciLexerSQL):
            comment = "--"
        elif isinstance(lexer, QsciLexerHTML):
            comment = None  # HTML uses block comments, skip

        if comment is None:
            return

        self.beginUndoAction()
        for line in range(start_line, end_line + 1):
            text = self.text(line)
            stripped = text.lstrip()
            indent = len(text) - len(stripped)
            if stripped.startswith(comment):
                new_text = text[:indent] + stripped[len(comment):].lstrip(" ", 1) if stripped[len(comment):].startswith(" ") else text[:indent] + stripped[len(comment):]
                self.setSelection(line, 0, line, len(text))
                self.replaceSelectedText(new_text.rstrip("\n"))
            else:
                self.setSelection(line, indent, line, indent)
                self.replaceSelectedText(comment + " ")
        self.endUndoAction()

    def indent_selection(self):
        self.SendScintilla(QsciScintilla.SCI_TAB)

    def unindent_selection(self):
        self.SendScintilla(QsciScintilla.SCI_BACKTAB)

    def duplicate_line(self):
        self.SendScintilla(QsciScintilla.SCI_LINEDUPLICATE)

    def move_line_up(self):
        self.SendScintilla(QsciScintilla.SCI_MOVESELECTEDLINESUP)

    def move_line_down(self):
        self.SendScintilla(QsciScintilla.SCI_MOVESELECTEDLINESDOWN)

    def get_stats(self):
        line, col = self.getCursorPosition()
        lines = self.lines()
        chars = len(self.text())
        sel = len(self.selectedText())
        return line + 1, col + 1, lines, chars, sel

    def set_language(self, ext):
        self._set_lexer_for_file(f"file{ext}")
