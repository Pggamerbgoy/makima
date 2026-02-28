"""
core/preferences_manager.py

User Preferences Manager
─────────────────────────
Remembers explicit user choices and implicitly tracks usage patterns.

Explicit preferences:
    "Set my default music app to Spotify"
    "Set anime default to Crunchyroll"

Implicit tracking:
    Records which app/platform is opened per category.
    Falls back to the most frequently used option when no explicit preference exists.

Usage:
    from core.preferences_manager import PreferencesManager

    prefs = PreferencesManager()
    prefs.set_explicit_preference("music", "spotify")
    prefs.record_usage("browser", "chrome")
    app = prefs.get_preference("music")   # → "spotify"
"""

import os
import json
import logging
from collections import defaultdict

logger = logging.getLogger("Makima.Preferences")

PREFERENCES_FILE = "user_preferences.json"


class PreferencesManager:
    """Handles explicit and implicit user preferences per usage category."""

    def __init__(self, filepath: str = PREFERENCES_FILE):
        self.filepath = filepath
        self.preferences: dict = {}                          # category → explicit value
        self.history: defaultdict = defaultdict(             # category → {value: count}
            lambda: defaultdict(int)
        )
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.preferences = data.get("explicit", {})
            for cat, counts in data.get("history", {}).items():
                for item, count in counts.items():
                    self.history[cat][item] = count
            logger.debug(f"Preferences loaded from {self.filepath}.")
        except Exception as e:
            logger.warning(f"Could not load preferences: {e}")

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {"explicit": self.preferences, "history": self.history},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.warning(f"Could not save preferences: {e}")

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_preference(self, category: str) -> str | None:
        """
        Return the preferred value for a category.
        Explicit preference wins; falls back to most-used implicit value.
        """
        category = category.lower().strip()
        if category in self.preferences:
            return self.preferences[category]
        if self.history[category]:
            return max(self.history[category].items(), key=lambda x: x[1])[0]
        return None

    # ── Mutation ──────────────────────────────────────────────────────────────

    def set_explicit_preference(self, category: str, value: str) -> str:
        """Store an explicit user preference and persist to disk."""
        category = category.lower().strip()
        value = value.strip()
        self.preferences[category] = value
        self._save()
        msg = f"Got it! I'll use {value} for {category} from now on."
        logger.info(f"Explicit preference: {category} → {value}")
        return msg

    def record_usage(self, category: str, value: str):
        """Implicitly track which app/platform the user opens per category."""
        if not value:
            return
        category = category.lower().strip()
        self.history[category][value.lower()] += 1
        self._save()

    def clear_preference(self, category: str) -> str:
        """Remove explicit preference for a category."""
        category = category.lower().strip()
        removed = self.preferences.pop(category, None)
        if removed:
            self._save()
            return f"Preference for {category} cleared."
        return f"No explicit preference found for {category}."

    def list_preferences(self) -> str:
        """Return a human-readable summary of all explicit preferences."""
        if not self.preferences:
            return "No explicit preferences saved yet."
        lines = [f"• {cat}: {val}" for cat, val in self.preferences.items()]
        return "Your preferences:\n" + "\n".join(lines)
