"""
ui/code_highlighter.py

Syntax Highlighting for Chat Bubbles
──────────────────────────────────────
Detects fenced code blocks (```lang ... ```) in messages and renders
them with colored syntax tokens using QTextEdit with custom formatting.
"""

import re
import logging
from PyQt5.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter
from PyQt5.QtCore import Qt

logger = logging.getLogger("Makima.CodeHighlighter")

# ─── Token colors ─────────────────────────────────────────────────────────────

COLORS = {
    "keyword":    "#c678dd",
    "string":     "#98c379",
    "comment":    "#5c6370",
    "number":     "#d19a66",
    "function":   "#61afef",
    "class":      "#e5c07b",
    "decorator":  "#56b6c2",
    "builtin":    "#e06c75",
    "operator":   "#56b6c2",
    "default":    "#abb2bf",
}

# ── Regex rules ───────────────────────────────────────────────────────────────

PYTHON_RULES = [
    # Decorators
    (r"@\w+", "decorator"),
    # Keywords
    (r"\b(?:def|class|return|if|elif|else|for|while|try|except|finally|"
     r"with|as|import|from|raise|pass|break|continue|yield|lambda|"
     r"async|await|and|or|not|in|is|None|True|False|global|nonlocal)\b",
     "keyword"),
    # Built-ins
    (r"\b(?:print|len|range|int|str|float|list|dict|set|tuple|"
     r"type|isinstance|enumerate|zip|map|filter|sorted|open|super|"
     r"self|cls|__init__|__name__|__main__)\b",
     "builtin"),
    # Function / class names
    (r"\bdef\s+(\w+)", "function"),
    (r"\bclass\s+(\w+)", "class"),
    # Strings (double and single quoted)
    (r'"""[\s\S]*?"""', "string"),
    (r"'''[\s\S]*?'''", "string"),
    (r'"[^"\\]*(?:\\.[^"\\]*)*"', "string"),
    (r"'[^'\\]*(?:\\.[^'\\]*)*'", "string"),
    # f-strings  (simplified)
    (r'f"[^"]*"', "string"),
    (r"f'[^']*'", "string"),
    # Numbers
    (r"\b\d+\.?\d*\b", "number"),
    # Comments
    (r"#[^\n]*", "comment"),
    # Operators
    (r"[+\-*/=<>!&|^~%]+", "operator"),
]


class PythonHighlighter(QSyntaxHighlighter):
    """Real-time syntax highlighter for QTextEdit."""

    def __init__(self, document):
        super().__init__(document)
        self._rules = []
        for pattern_str, token_type in PYTHON_RULES:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(COLORS.get(token_type, COLORS["default"])))
            if token_type == "keyword":
                fmt.setFontWeight(QFont.Bold)
            elif token_type == "comment":
                fmt.setFontItalic(True)
            self._rules.append((re.compile(pattern_str), fmt))

    def highlightBlock(self, text: str):
        for regex, fmt in self._rules:
            for match in regex.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)


class CodeHighlighter:
    """Static utilities for rendering highlighted code in chat bubbles."""

    @staticmethod
    def create_highlighted_widget(message: str) -> QWidget:
        """
        Parse a message for fenced code blocks and return a QWidget
        that interleaves plain text QLabels with highlighted QTextEdits.
        """
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Split on fenced code blocks
        parts = re.split(r"```(\w*)\n?([\s\S]*?)```", message)
        # parts = [text_before, lang, code, text_after, lang2, code2, ...]

        i = 0
        while i < len(parts):
            if i % 3 == 0:
                # Plain text segment
                text = parts[i].strip()
                if text:
                    label = QLabel(text)
                    label.setWordWrap(True)
                    label.setTextInteractionFlags(
                        Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
                    )
                    label.setObjectName("messageText")
                    layout.addWidget(label)
            elif i % 3 == 2:
                # Code block
                code = parts[i]
                editor = QTextEdit()
                editor.setReadOnly(True)
                editor.setPlainText(code)
                editor.setFont(QFont("Consolas", 11))
                editor.setStyleSheet(
                    "QTextEdit {"
                    "  background-color: #1e1e2e;"
                    "  color: #abb2bf;"
                    "  border: 1px solid #2a3155;"
                    "  border-radius: 8px;"
                    "  padding: 10px;"
                    "}"
                )
                # Auto-height
                doc = editor.document()
                doc.setDocumentMargin(8)
                height = int(doc.size().height()) + 24
                editor.setFixedHeight(min(height, 400))  # cap at 400px

                # Apply syntax highlighting
                PythonHighlighter(editor.document())

                layout.addWidget(editor)
            i += 1

        container.setLayout(layout)
        return container
