"""
TOOL: Command Shortcut Expander
──────────────────────────────────────────────
Lets users define personal shortcuts so Makima
understands "wm" → "what's the weather in Mumbai"
or "gm" → "play my morning playlist and read my emails"

Shortcuts are learned automatically from repeated patterns
OR set manually by user.

USAGE in command_router.py (before routing):
    from tools.shortcut_expander import ShortcutExpander
    expander = ShortcutExpander()

    # Expand before routing:
    expanded = expander.expand(user_input)
    # Then route expanded command

    # Auto-learn from usage:
    expander.record_usage(user_input)
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter


SHORTCUTS_FILE = Path("makima_memory/shortcuts.json")
USAGE_LOG_FILE = Path("makima_memory/usage_log.json")
AUTO_SHORTCUT_THRESHOLD = 5   # suggest shortcut after 5 repetitions
MAX_SHORTCUTS = 100


class ShortcutExpander:

    def __init__(self):
        SHORTCUTS_FILE.parent.mkdir(exist_ok=True)
        self.shortcuts = self._load_shortcuts()
        self.usage_log = self._load_usage()

    # ── Public API ────────────────────────────────────────────────────────────

    def expand(self, text: str) -> str:
        """
        Expand shortcut if one matches, else return original.
        Case-insensitive.
        """
        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # Exact match
        if text_lower in self.shortcuts:
            expanded = self.shortcuts[text_lower]["expansion"]
            self.shortcuts[text_lower]["uses"] += 1
            self._save_shortcuts()
            print(f"[Shortcuts] '{text_stripped}' → '{expanded}'")
            return expanded

        # Prefix match (e.g. "em john" where "em" = "send email to")
        for shortcut, data in self.shortcuts.items():
            if text_lower.startswith(shortcut + " "):
                suffix = text_stripped[len(shortcut):].strip()
                expanded = data["expansion"] + " " + suffix
                data["uses"] += 1
                self._save_shortcuts()
                print(f"[Shortcuts] '{shortcut}' prefix → '{expanded}'")
                return expanded

        return text_stripped  # No match, pass through

    def add(self, shortcut: str, expansion: str, description: str = ""):
        """
        Manually add a shortcut.
        add("wm", "what's the weather in Mumbai")
        add("gm", "play my morning playlist and read my emails")
        """
        if len(self.shortcuts) >= MAX_SHORTCUTS:
            print("[Shortcuts] Max shortcuts reached, remove one first")
            return False

        self.shortcuts[shortcut.lower().strip()] = {
            "expansion": expansion,
            "description": description,
            "uses": 0,
            "created": time.time(),
            "auto": False
        }
        self._save_shortcuts()
        print(f"[Shortcuts] Added: '{shortcut}' → '{expansion}'")
        return True

    def remove(self, shortcut: str) -> bool:
        """Remove a shortcut."""
        key = shortcut.lower().strip()
        if key in self.shortcuts:
            del self.shortcuts[key]
            self._save_shortcuts()
            return True
        return False

    def list_all(self) -> List[Dict]:
        """Return all shortcuts sorted by usage."""
        result = []
        for key, data in self.shortcuts.items():
            result.append({
                "shortcut": key,
                "expansion": data["expansion"],
                "uses": data["uses"],
                "auto": data.get("auto", False),
                "description": data.get("description", "")
            })
        return sorted(result, key=lambda x: x["uses"], reverse=True)

    def record_usage(self, command: str):
        """
        Call this for every command Makima receives.
        Automatically suggests shortcuts for repeated commands.
        """
        command_lower = command.lower().strip()

        # Skip very short or already-shortcutted commands
        if len(command_lower) < 10 or command_lower in self.shortcuts.values():
            return

        self.usage_log[command_lower] = self.usage_log.get(command_lower, 0) + 1
        self._save_usage()

        # Suggest auto-shortcut if threshold hit
        count = self.usage_log[command_lower]
        if count == AUTO_SHORTCUT_THRESHOLD:
            self._suggest_shortcut(command)

    def get_suggestions(self) -> List[Dict]:
        """
        Get commands that are repeated often enough to warrant a shortcut.
        """
        suggestions = []
        for command, count in self.usage_log.items():
            if count >= AUTO_SHORTCUT_THRESHOLD and command not in [
                v["expansion"].lower() for v in self.shortcuts.values()
            ]:
                # Generate a suggested shortcut key
                words = command.split()
                suggested_key = "".join(w[0] for w in words[:3])  # initials
                suggestions.append({
                    "command": command,
                    "count": count,
                    "suggested_shortcut": suggested_key
                })

        return sorted(suggestions, key=lambda x: x["count"], reverse=True)

    def auto_create_suggested(self, command: str, shortcut: str = None):
        """
        Auto-create a shortcut for a frequently used command.
        Optionally specify the shortcut key, else auto-generate.
        """
        if not shortcut:
            words = command.split()
            shortcut = "".join(w[0] for w in words[:3]).lower()

            # Avoid collisions
            base = shortcut
            i = 2
            while shortcut in self.shortcuts:
                shortcut = base + str(i)
                i += 1

        return self.add(shortcut, command, description="Auto-created from frequent use")

    # ── Built-in default shortcuts ────────────────────────────────────────────

    def load_defaults(self):
        """
        Load sensible defaults. Call once on first run.
        User can override these.
        """
        defaults = {
            "gm":    ("good morning briefing", "Morning routine"),
            "gn":    ("goodnight shutdown routine", "Night routine"),
            "wb":    ("what's the weather today", "Quick weather"),
            "mu":    ("volume up", "Volume up"),
            "md":    ("volume down", "Volume down"),
            "ss":    ("take a screenshot", "Screenshot"),
            "news":  ("read me today's top news headlines", "Daily news"),
            "focus": ("enable focus mode for 2 hours", "Focus mode"),
        }

        added = 0
        for shortcut, (expansion, desc) in defaults.items():
            if shortcut not in self.shortcuts:
                self.add(shortcut, expansion, desc)
                added += 1

        print(f"[Shortcuts] Loaded {added} default shortcuts")

    # ── Internals ─────────────────────────────────────────────────────────────

    def _suggest_shortcut(self, command: str):
        """Print a suggestion (hook this into Makima's speech)."""
        words = command.split()
        suggestion = "".join(w[0] for w in words[:3]).lower()
        print(f"[Shortcuts] 💡 You've said '{command}' {AUTO_SHORTCUT_THRESHOLD} times. "
              f"Want me to create shortcut '{suggestion}' for it?")

    def _load_shortcuts(self) -> Dict:
        if SHORTCUTS_FILE.exists():
            try:
                return json.loads(SHORTCUTS_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _load_usage(self) -> Dict:
        if USAGE_LOG_FILE.exists():
            try:
                return json.loads(USAGE_LOG_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _save_shortcuts(self):
        SHORTCUTS_FILE.write_text(json.dumps(self.shortcuts, indent=2))

    def _save_usage(self):
        USAGE_LOG_FILE.write_text(json.dumps(self.usage_log, indent=2))
