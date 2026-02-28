"""
systems/clipboard_monitor.py
Watches clipboard for URLs and offers to open them.
"""

import time
import logging
import re
from typing import Callable

logger = logging.getLogger("Makima.ClipboardMonitor")

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

URL_PATTERN = re.compile(r'https?://[^\s]+')


class ClipboardMonitor:

    CHECK_INTERVAL = 3  # seconds

    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._last_clipboard = ""
        self._running = True

    def run(self):
        if not PYPERCLIP_AVAILABLE:
            return
        while self._running:
            try:
                content = pyperclip.paste()
                if content != self._last_clipboard:
                    self._last_clipboard = content
                    if URL_PATTERN.match(content.strip()):
                        self.callback(f"I noticed you copied a link. Want me to open it?")
            except Exception:
                pass
            time.sleep(self.CHECK_INTERVAL)
