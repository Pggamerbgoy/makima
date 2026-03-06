"""Code editor widget — QScintilla with VS Code style."""
import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.Qsci import (
    QsciScintilla, QsciLexerPython, QsciLexerJavaScript,
    QsciLexerHTML, QsciLexerCSS, QsciLexerCPP, QsciLexerJSON,
    QsciLexerBash, QsciLexerSQL, QsciLexerMarkdown,
    QsciLexerYAML, QsciLexerXML
)
from editor.themes import get_theme

LEXERS = {
    ".py": QsciLexerPython,   ".js": QsciLexerJavaScript,
    ".ts": QsciLexerJavaScript, ".jsx": QsciLexerJavaScript,
    ".tsx": QsciLexerJavaScript, ".html": QsciLexerHTML,
    ".htm": QsciLexerHTML,    ".css": QsciLexerCSS,
    ".scss": QsciLexerCSS,    ".cpp": QsciLexerCPP,
    ".c": QsciLexerCPP,       ".h": QsciLexerCPP,
    ".hpp": QsciLexerCPP,     ".json": QsciLexerJSON,
    ".sh": QsciLexerBash,     ".bash": QsciLexerBash,
    ".sql": QsciLexerSQL,     ".md": QsciLexerMarkdown,
    ".yaml": QsciLexerYAML,   ".yml": QsciLexerYAML,
    ".xml": QsciLexerXML,
}

def c(h): return QColor(h)

MONO_FONT = "Cascadia Code"
MONO_FALLBACK = "Consolas"

class CodeEditor(QsciScintilla):
    file_path = None
    is_modified = False
    modified_changed = pyqtSignal(bool)

    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)
        self.file_path = file_path
        self._setup()
        self._theme()
        if file_path:
            self._set_lexer(file_path)

    def _mono(self, size=13):
        f = QFont(MONO_FONT, size)
        if not f.exactMatch():
            f = QFont(MONO_FALLBACK, size)
        f.setFixedPitch(True)
        return f

    def _setup(self):
        t = get_theme()
        self.setFont(self._mono(13))

        # Line numbers
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "00000")
        self.setMarginsFont(self._mono(11))

        # Fold margin
        self.setMarginType(2, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(2, 14)
        self.setMarginSensitivity(2, True)
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 2)

        # Indent
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        self.setIndentationGuides(True)

        # Brace match
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

        # Autocomplete
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionCaseSensitivity(False)

        # Edge ruler at col 80
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(80)

        # Caret line
        self.setCaretLineVisible(True)
        self.setCaretWidth(2)

        # Scroll
        self.setScrollWidthTracking(True)
        self.setEolMode(QsciScintilla.EolMode.EolUnix)
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # Multi-cursor
        self.SendScintilla(QsciScintilla.SCI_SETMULTIPLESELECTION, 1)
        self.SendScintilla(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING, 1)

        self.textChanged.connect(self._dirty)

    def _dirty(self):
        if not self.is_modified:
            self.is_modified = True
            self.modified_changed.emit(True)

    def mark_saved(self):
        self.is_modified = False
        self.modified_changed.emit(False)

    def _theme(self):
        t = get_theme()
        self.setPaper(c(t["ed_bg"]))
        self.setColor(c(t["ed_fg"]))
        self.setMarginsBackgroundColor(c(t["ed_margin_bg"]))
        self.setMarginsForegroundColor(c(t["ed_margin_fg"]))
        self.setSelectionBackgroundColor(c(t["ed_sel"]))
        self.setSelectionForegroundColor(c(t["ed_fg"]))
        self.setCaretForegroundColor(c(t["ed_caret"]))
        self.setCaretLineBackgroundColor(c(t["ed_line_highlight"]))
        self.setEdgeColor(c(t["ed_ruler"]))
        self.setIndentationGuidesBackgroundColor(c(t["ed_bg"]))
        self.setIndentationGuidesForegroundColor(c(t["ed_indent_guide"]))
        self.setMatchedBraceBackgroundColor(c(t["bg_selection"] if "bg_selection" in t else t["ed_sel"]))
        self.setMatchedBraceForegroundColor(c(t["fg"]))
        self.setFoldMarginColors(c(t["ed_margin_bg"]), c(t["ed_margin_bg"]))

    def _set_lexer(self, path):
        ext = os.path.splitext(path)[1].lower()
        cls = LEXERS.get(ext)
        if cls:
            self._apply_lexer(cls())
        else:
            self.setLexer(None)

    def _apply_lexer(self, lexer):
        t = get_theme()
        font = self._mono(13)
        lexer.setFont(font)
        lexer.setDefaultPaper(c(t["ed_bg"]))
        lexer.setDefaultColor(c(t["ed_fg"]))

        # Paint all style backgrounds
        for style in range(128):
            lexer.setPaper(c(t["ed_bg"]), style)

        if isinstance(lexer, QsciLexerPython):
            lexer.setColor(c(t["syn_keyword"]),   QsciLexerPython.Keyword)
            lexer.setColor(c(t["syn_string"]),    QsciLexerPython.SingleQuotedString)
            lexer.setColor(c(t["syn_string"]),    QsciLexerPython.DoubleQuotedString)
            lexer.setColor(c(t["syn_string"]),    QsciLexerPython.TripleSingleQuotedString)
            lexer.setColor(c(t["syn_string"]),    QsciLexerPython.TripleDoubleQuotedString)
            lexer.setColor(c(t["syn_comment"]),   QsciLexerPython.Comment)
            lexer.setColor(c(t["syn_comment"]),   QsciLexerPython.CommentBlock)
            lexer.setColor(c(t["syn_number"]),    QsciLexerPython.Number)
            lexer.setColor(c(t["syn_decorator"]), QsciLexerPython.Decorator)
            lexer.setColor(c(t["syn_class"]),     QsciLexerPython.ClassName)
            lexer.setColor(c(t["syn_function"]),  QsciLexerPython.FunctionMethodName)
            lexer.setColor(c(t["syn_builtin"]),   QsciLexerPython.HighlightedIdentifier)

        elif isinstance(lexer, QsciLexerJavaScript):
            lexer.setColor(c(t["syn_keyword"]),  QsciLexerJavaScript.Keyword)
            lexer.setColor(c(t["syn_string"]),   QsciLexerJavaScript.SingleQuotedString)
            lexer.setColor(c(t["syn_string"]),   QsciLexerJavaScript.DoubleQuotedString)
            lexer.setColor(c(t["syn_comment"]),  QsciLexerJavaScript.CommentLine)
            lexer.setColor(c(t["syn_comment"]),  QsciLexerJavaScript.Comment)
            lexer.setColor(c(t["syn_number"]),   QsciLexerJavaScript.Number)

        elif isinstance(lexer, QsciLexerCPP):
            lexer.setColor(c(t["syn_keyword"]),  QsciLexerCPP.Keyword)
            lexer.setColor(c(t["syn_string"]),   QsciLexerCPP.DoubleQuotedString)
            lexer.setColor(c(t["syn_comment"]),  QsciLexerCPP.CommentLine)
            lexer.setColor(c(t["syn_comment"]),  QsciLexerCPP.Comment)
            lexer.setColor(c(t["syn_number"]),   QsciLexerCPP.Number)
            lexer.setColor(c(t["syn_builtin"]),  QsciLexerCPP.PreProcessor)

        self.setLexer(lexer)

    def refresh_theme(self):
        self._theme()
        if self.lexer():
            self._apply_lexer(self.lexer().__class__())

    def goto_line(self, line):
        self.setCursorPosition(line - 1, 0)
        self.ensureCursorVisible()

    def find_text(self, text, case=False, whole=False, regex=False, forward=True):
        return self.findFirst(text, regex, case, whole, True, forward)

    def replace_text(self, find, replace, case=False, whole=False, regex=False):
        if self.findFirst(find, regex, case, whole, True):
            self.replace(replace); return True
        return False

    def replace_all(self, find, replace, case=False, whole=False, regex=False):
        count = 0
        self.beginUndoAction()
        if self.findFirst(find, regex, case, whole, True):
            self.replace(replace); count += 1
            while self.findNext():
                self.replace(replace); count += 1
        self.endUndoAction()
        return count

    def toggle_comment(self):
        if self.hasSelectedText():
            sl, _, el, _ = self.getSelection()
        else:
            sl = el = self.getCursorPosition()[0]
        lexer = self.lexer()
        comment = "#"
        if isinstance(lexer, (QsciLexerJavaScript, QsciLexerCPP)): comment = "//"
        elif isinstance(lexer, QsciLexerSQL): comment = "--"
        self.beginUndoAction()
        for line in range(sl, el + 1):
            text = self.text(line)
            stripped = text.lstrip()
            indent = len(text) - len(stripped)
            if stripped.startswith(comment + " "):
                new = text[:indent] + stripped[len(comment)+1:]
            elif stripped.startswith(comment):
                new = text[:indent] + stripped[len(comment):]
            else:
                new = text[:indent] + comment + " " + stripped
            self.setSelection(line, 0, line, len(text))
            self.replaceSelectedText(new.rstrip("\n"))
        self.endUndoAction()

    def duplicate_line(self): self.SendScintilla(QsciScintilla.SCI_LINEDUPLICATE)
    def move_line_up(self):   self.SendScintilla(QsciScintilla.SCI_MOVESELECTEDLINESUP)
    def move_line_down(self): self.SendScintilla(QsciScintilla.SCI_MOVESELECTEDLINESDOWN)
    def indent_selection(self):   self.SendScintilla(QsciScintilla.SCI_TAB)
    def unindent_selection(self): self.SendScintilla(QsciScintilla.SCI_BACKTAB)

    def get_stats(self):
        line, col = self.getCursorPosition()
        return line+1, col+1, self.lines(), len(self.text()), len(self.selectedText())

    def set_language(self, ext):
        self._set_lexer(f"file{ext}")
