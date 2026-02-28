"""
systems/app_control.py
Open and close applications with fuzzy name matching.
Supports Windows (Start Menu scan) and Linux (PATH scan).
"""

import os
import re
import json
import logging
import subprocess
import platform
from typing import Optional

logger = logging.getLogger("Makima.AppControl")
OS = platform.system()

APPS_INDEX_FILE = "app_index.json"
CUSTOM_APPS_FILE = "custom_apps.json"

# Common web app shortcuts
WEB_APPS = {
    "youtube": "https://youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://google.com",
    "twitter": "https://twitter.com",
    "reddit": "https://reddit.com",
    "github": "https://github.com",
    "netflix": "https://netflix.com",
    "spotify web": "https://open.spotify.com",
    "crunchyroll": "https://crunchyroll.com",
    "whatsapp web": "https://web.whatsapp.com",
}


def _fuzzy_score(query: str, candidate: str) -> float:
    """Simple word-overlap fuzzy score."""
    q_words = set(query.lower().split())
    c_words = set(candidate.lower().split())
    if not q_words or not c_words:
        return 0.0
    overlap = len(q_words & c_words)
    return overlap / max(len(q_words), len(c_words))


class AppControl:

    def __init__(self):
        self.app_index: dict[str, str] = {}  # name → executable path
        self.custom_apps: dict[str, str] = self._load_custom_apps()
        self._load_index()

    # ─── Index Management ─────────────────────────────────────────────────────

    def _load_custom_apps(self) -> dict:
        if os.path.exists(CUSTOM_APPS_FILE):
            try:
                with open(CUSTOM_APPS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _load_index(self):
        if os.path.exists(APPS_INDEX_FILE):
            try:
                with open(APPS_INDEX_FILE, "r") as f:
                    self.app_index = json.load(f)
                logger.info(f"📦 App index loaded: {len(self.app_index)} apps.")
                return
            except Exception:
                pass
        self.scan()

    def scan(self) -> str:
        """Scan the system for installed applications."""
        logger.info("🔍 Scanning for installed apps...")
        found: dict[str, str] = {}

        if OS == "Windows":
            # Scan Start Menu shortcuts
            start_dirs = [
                os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"),
                             "Microsoft\\Windows\\Start Menu\\Programs"),
                os.path.join(os.environ.get("APPDATA", ""),
                             "Microsoft\\Windows\\Start Menu\\Programs"),
            ]
            for d in start_dirs:
                if not os.path.isdir(d):
                    continue
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.endswith(".lnk"):
                            name = f[:-4].lower()
                            found[name] = os.path.join(root, f)

            # Also scan common install dirs
            prog_dirs = [
                os.environ.get("ProgramFiles", "C:\\Program Files"),
                os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                os.environ.get("LOCALAPPDATA", ""),
            ]
            for d in prog_dirs:
                if not os.path.isdir(d):
                    continue
                for item in os.listdir(d):
                    item_path = os.path.join(d, item)
                    if os.path.isdir(item_path):
                        exe = os.path.join(item_path, f"{item}.exe")
                        if os.path.exists(exe):
                            found[item.lower()] = exe

        elif OS == "Linux":
            # Scan .desktop files
            desktop_dirs = [
                "/usr/share/applications",
                os.path.expanduser("~/.local/share/applications"),
            ]
            for d in desktop_dirs:
                if not os.path.isdir(d):
                    continue
                for f in os.listdir(d):
                    if f.endswith(".desktop"):
                        name = f[:-8].lower()
                        found[name] = os.path.join(d, f)

        self.app_index = found
        try:
            with open(APPS_INDEX_FILE, "w") as f:
                json.dump(found, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save app index: {e}")

        logger.info(f"✅ Found {len(found)} apps.")
        return f"App scan complete. Found {len(found)} applications."

    # ─── Lookup ───────────────────────────────────────────────────────────────

    def _find_app(self, query: str) -> Optional[tuple[str, str]]:
        """Return (name, path) for the best match or None."""
        query_lower = query.lower().strip()

        # Exact match first
        if query_lower in self.custom_apps:
            return query_lower, self.custom_apps[query_lower]
        if query_lower in self.app_index:
            return query_lower, self.app_index[query_lower]

        # Web apps
        if query_lower in WEB_APPS:
            return query_lower, WEB_APPS[query_lower]

        # Fuzzy match across all sources
        all_apps = {**self.app_index, **self.custom_apps}
        best_name, best_path, best_score = None, None, 0.0
        for name, path in all_apps.items():
            score = _fuzzy_score(query_lower, name)
            if score > best_score:
                best_score = score
                best_name = name
                best_path = path

        if best_score >= 0.5:
            return best_name, best_path
        return None

    # ─── Actions ──────────────────────────────────────────────────────────────

    def open(self, app_name: str) -> str:
        result = self._find_app(app_name)
        if not result:
            return f"I couldn't find an app called '{app_name}'. Try 'scan apps' to rebuild the index."

        name, path = result

        try:
            if path.startswith("http"):
                import webbrowser
                webbrowser.open(path)
                return f"Opening {name} in your browser."

            if OS == "Windows":
                os.startfile(path)
            elif OS == "Linux":
                if path.endswith(".desktop"):
                    subprocess.Popen(["gtk-launch", os.path.basename(path)[:-8]])
                else:
                    subprocess.Popen([path])
            elif OS == "Darwin":
                subprocess.Popen(["open", path])
            return f"Opening {name}."
        except Exception as e:
            logger.error(f"Failed to open {name}: {e}")
            return f"Couldn't open {name}: {e}"

    def close(self, app_name: str) -> str:
        try:
            import psutil
            app_lower = app_name.lower()
            killed = []
            for proc in psutil.process_iter(['name', 'pid']):
                proc_name = proc.info['name'].lower()
                if app_lower in proc_name or _fuzzy_score(app_lower, proc_name) > 0.6:
                    proc.terminate()
                    killed.append(proc.info['name'])
            if killed:
                return f"Closed: {', '.join(set(killed))}."
            return f"No running process found for '{app_name}'."
        except ImportError:
            if OS == "Windows":
                subprocess.run(["taskkill", "/F", "/IM", f"{app_name}.exe"], capture_output=True)
                return f"Attempted to close {app_name}."
            return "psutil not installed. Can't close apps."
        except Exception as e:
            return f"Failed to close {app_name}: {e}"
