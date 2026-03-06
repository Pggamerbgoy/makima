"""Integrated terminal panel using QProcess."""
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QLineEdit, QTabWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCursor, QKeySequence, QShortcut
from editor.themes import get_theme


class TerminalInstance(QWidget):
    """One terminal tab."""
    def __init__(self, shell=None, cwd=None, parent=None):
        super().__init__(parent)
        self.process = None
        self.history = []
        self.hist_idx = -1
        self._cwd = cwd or os.path.expanduser("~")
        self._shell = shell or self._detect_shell()
        self._setup_ui()
        self._start_process()

    def _detect_shell(self):
        if sys.platform == "win32":
            return "cmd.exe"
        return os.environ.get("SHELL", "/bin/bash")

    def _setup_ui(self):
        t = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.output = QPlainTextEdit()
        self.output.setObjectName("terminal")
        self.output.setReadOnly(True)
        self.output.setFont(QFont("JetBrains Mono", 12))
        self.output.setMaximumBlockCount(5000)
        self.output.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {t['term_bg']};
                color: {t['term_fg']};
                border: none;
                padding: 8px;
                font-family: 'JetBrains Mono';
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.output)

        # Input row
        input_row = QWidget()
        input_row.setFixedHeight(34)
        input_row.setStyleSheet(f"background: {t['term_bg']}; border-top: 1px solid {t['border']};")
        ir = QHBoxLayout(input_row)
        ir.setContentsMargins(8, 4, 8, 4)
        ir.setSpacing(6)

        prompt = QLabel("❯")
        prompt.setStyleSheet(f"color: {t['accent']}; font-size: 14px; font-family: 'JetBrains Mono';")
        ir.addWidget(prompt)

        self.input = QLineEdit()
        self.input.setFont(QFont("JetBrains Mono", 12))
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; border: none;
                color: {t['term_fg']}; font-size: 12px;
                font-family: 'JetBrains Mono';
            }}
        """)
        self.input.returnPressed.connect(self._send_command)
        self.input.installEventFilter(self)
        ir.addWidget(self.input)

        layout.addWidget(input_row)
        self.input.setFocus()

    def _start_process(self):
        self.process = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(self._cwd)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)

        if sys.platform == "win32":
            self.process.start(self._shell, [])
        else:
            self.process.start(self._shell, ["-i"])

        self._append(f"Volt Terminal — {self._shell}\n", "#94a3b8")

    def _on_stdout(self):
        data = self.process.readAllStandardOutput().data().decode(errors="replace")
        self._append(data)

    def _on_stderr(self):
        data = self.process.readAllStandardError().data().decode(errors="replace")
        t = get_theme()
        self._append(data, t["red"])

    def _on_finished(self, code, status):
        self._append(f"\n[Process exited with code {code}]\n", "#94a3b8")

    def _append(self, text, color=None):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if color:
            fmt = cursor.charFormat()
            fmt.setForeground(QColor(color))
            cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _send_command(self):
        cmd = self.input.text()
        if not cmd.strip():
            return
        self.history.append(cmd)
        self.hist_idx = len(self.history)
        self.input.clear()
        t = get_theme()
        self._append(f"❯ {cmd}\n", t["accent"])
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write((cmd + "\n").encode())
        else:
            self._run_detached(cmd)

    def _run_detached(self, cmd):
        proc = QProcess(self)
        proc.setWorkingDirectory(self._cwd)
        proc.readyReadStandardOutput.connect(
            lambda: self._append(proc.readAllStandardOutput().data().decode(errors="replace"))
        )
        proc.readyReadStandardError.connect(
            lambda: self._append(proc.readAllStandardError().data().decode(errors="replace"),
                                  get_theme()["red"])
        )
        if sys.platform == "win32":
            proc.start("cmd.exe", ["/c", cmd])
        else:
            proc.start("/bin/sh", ["-c", cmd])

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        if obj == self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                if self.history and self.hist_idx > 0:
                    self.hist_idx -= 1
                    self.input.setText(self.history[self.hist_idx])
                return True
            elif event.key() == Qt.Key.Key_Down:
                if self.hist_idx < len(self.history) - 1:
                    self.hist_idx += 1
                    self.input.setText(self.history[self.hist_idx])
                else:
                    self.hist_idx = len(self.history)
                    self.input.clear()
                return True
            elif event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if self.process:
                    self.process.kill()
                return True
        return super().eventFilter(obj, event)

    def set_cwd(self, path):
        self._cwd = path
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write(f"cd {path}\n".encode())

    def clear(self):
        self.output.clear()

    def kill(self):
        if self.process:
            self.process.kill()


class TerminalPanel(QWidget):
    """Multi-tab terminal panel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        t = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_row = QWidget()
        header_row.setFixedHeight(32)
        header_row.setStyleSheet(f"background: {t['bg2']}; border-bottom: 1px solid {t['border']};")
        hr = QHBoxLayout(header_row)
        hr.setContentsMargins(8, 0, 8, 0)

        lbl = QLabel("TERMINAL")
        lbl.setStyleSheet(f"color: {t['text3']}; font-size: 10px; font-weight: 600; letter-spacing: 2px;")
        hr.addWidget(lbl)
        hr.addStretch()

        for icon, tip, fn in [
            ("＋", "New Terminal", self.new_terminal),
            ("✕", "Kill Terminal", self._kill_current),
            ("⊡", "Clear", self._clear_current),
        ]:
            btn = QPushButton(icon)
            btn.setFixedSize(24, 24)
            btn.setToolTip(tip)
            btn.clicked.connect(fn)
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: none; color: {t['text2']}; font-size: 12px; border-radius: 4px; }}
                QPushButton:hover {{ background: {t['bg4']}; color: {t['text']}; }}
            """)
            hr.addWidget(btn)

        layout.addWidget(header_row)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ background: {t['term_bg']}; border: none; }}
            QTabBar::tab {{
                background: {t['bg2']}; color: {t['text2']};
                border: none; border-right: 1px solid {t['border']};
                padding: 4px 12px; font-size: 11px; min-width: 80px;
            }}
            QTabBar::tab:selected {{
                background: {t['term_bg']}; color: {t['text']};
                border-bottom: 2px solid {t['green']};
            }}
        """)
        layout.addWidget(self.tabs)

        self.new_terminal()

    def new_terminal(self, cwd=None):
        term = TerminalInstance(cwd=cwd)
        idx = self.tabs.addTab(term, f"bash {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(idx)
        term.input.setFocus()
        return term

    def _close_tab(self, idx):
        term = self.tabs.widget(idx)
        if term:
            term.kill()
        if self.tabs.count() > 1:
            self.tabs.removeTab(idx)
        else:
            term.clear()
            self.new_terminal()
            self.tabs.removeTab(0)

    def _kill_current(self):
        term = self.tabs.currentWidget()
        if term:
            term.kill()

    def _clear_current(self):
        term = self.tabs.currentWidget()
        if term:
            term.clear()

    def set_cwd(self, path):
        term = self.tabs.currentWidget()
        if term:
            term.set_cwd(path)

    def run_command(self, cmd):
        term = self.tabs.currentWidget()
        if not term:
            term = self.new_terminal()
        term.input.setText(cmd)
        term._send_command()
