#!/usr/bin/env python3
"""
Volt Code Editor — Professional PyQt6 Code Editor
Run: pip install PyQt6 PyQt6-QScintilla && python main.py
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from editor.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Volt")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VoltIDE")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
