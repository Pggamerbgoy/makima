"""
systems/focus_mode.py
Productivity mode: kills distracting apps automatically.
"""

import os
import json
import time
import threading
import logging
import platform

logger = logging.getLogger("Makima.FocusMode")
OS = platform.system()

FOCUS_CONFIG = "focus_config.json"
DEFAULT_BLOCKED = [
    "chrome", "firefox", "discord", "steam", "riot client", "epicgameslauncher",
    "spotify", "netflix", "twitch", "youtube music",
]


class FocusMode:

    def __init__(self):
        self.active = False
        self._monitor_thread = None
        self.blocked_apps = self._load_config()

    def _load_config(self) -> list[str]:
        if os.path.exists(FOCUS_CONFIG):
            try:
                with open(FOCUS_CONFIG) as f:
                    return json.load(f).get("blocked", DEFAULT_BLOCKED)
            except Exception:
                pass
        return DEFAULT_BLOCKED

    def start(self) -> str:
        if self.active:
            return "Focus mode is already on."
        self.active = True
        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self._monitor_thread.start()
        return "Focus mode activated. Distracting apps will be closed automatically."

    def stop(self) -> str:
        self.active = False
        return "Focus mode deactivated. You can relax now."

    def _monitor(self):
        try:
            import psutil
        except ImportError:
            logger.warning("psutil not available. Focus mode monitoring disabled.")
            return

        while self.active:
            for proc in psutil.process_iter(['name']):
                name = proc.info['name'].lower()
                for blocked in self.blocked_apps:
                    if blocked in name:
                        try:
                            proc.terminate()
                            logger.info(f"Focus mode: closed {proc.info['name']}")
                        except Exception:
                            pass
            time.sleep(10)
