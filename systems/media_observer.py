"""
systems/media_observer.py
Tracks what media you're listening to or watching.
"""

import time
import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger("Makima.MediaObserver")


class MediaObserver:
    """Watches currently playing media and logs it."""

    def __init__(self, callback: Callable[[str], None] = None):
        self._callback = callback
        self._last_media: Optional[str] = None
        self._running = True

    def get_last(self) -> str:
        if self._last_media:
            return f"Last I saw, you were listening to: {self._last_media}"
        return "I don't have any record of recent media."

    def run(self):
        """Background loop — tries to detect media via platform APIs."""
        while self._running:
            try:
                self._detect_media()
            except Exception:
                pass
            time.sleep(15)

    def _detect_media(self):
        import platform
        OS = platform.system()
        if OS == "Windows":
            try:
                # Windows: read via Windows Media Session API (asyncio-based)
                # Simplified polling approach
                import subprocess
                result = subprocess.run(
                    ["powershell", "-Command",
                     "(Get-Process | Where-Object {$_.MainWindowTitle -ne ''}).MainWindowTitle"],
                    capture_output=True, text=True, timeout=3
                )
                titles = result.stdout.strip().split("\n")
                for title in titles:
                    if any(kw in title.lower() for kw in ["spotify", "youtube", "music", "player"]):
                        if self._last_media != title.strip():
                            self._last_media = title.strip()
                            if self._callback:
                                self._callback(self._last_media)
                        break
            except Exception:
                pass
