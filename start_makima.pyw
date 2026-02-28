"""
🌸 Makima AI Assistant — Double-click Launcher
───────────────────────────────────────────────
.pyw extension = no console window on Windows.
Just double-click this file to launch Makima with the full desktop UI.
"""

import sys
import os

# Ensure we're running from the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from makima_assistant import MakimaAssistant

makima = MakimaAssistant(ui_mode=True)
makima.run()
