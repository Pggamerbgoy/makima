"""
ui/chat_history.py

Chat History Manager
─────────────────────
Persists chat sessions to disk as JSON. Supports:
  • Rolling session files (per-day)
  • Full-text search across sessions
  • Recent-message retrieval for UI warm-up
"""

import os
import json
import logging
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger("Makima.ChatHistory")

HISTORY_DIR = Path("makima_memory") / "chat_history"


class ChatHistory:
    """Manages persistent chat session storage."""

    def __init__(self):
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        self._session_file = HISTORY_DIR / f"session_{date.today().isoformat()}.json"
        self._messages: list[dict] = []
        self._load_session()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_session(self):
        if self._session_file.exists():
            try:
                with open(self._session_file, "r", encoding="utf-8") as f:
                    self._messages = json.load(f)
            except Exception:
                self._messages = []
        else:
            self._messages = []

    def save(self):
        """Flush current session to disk."""
        try:
            with open(self._session_file, "w", encoding="utf-8") as f:
                json.dump(self._messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save chat history: {e}")

    # ── Add / Query ───────────────────────────────────────────────────────────

    def add_message(self, message: str, is_user: bool, files: list = None):
        entry = {
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "date":      datetime.now().isoformat(),
            "message":   message,
            "is_user":   is_user,
            "files":     files or [],
        }
        self._messages.append(entry)
        # Auto-save every 5 messages
        if len(self._messages) % 5 == 0:
            self.save()

    def get_recent_messages(self, count: int = 20) -> list[dict]:
        """Return the most recent *count* messages from today's session."""
        return self._messages[-count:]

    def get_sessions(self) -> list[dict]:
        """Return metadata about all saved session files."""
        sessions = []
        for path in sorted(HISTORY_DIR.glob("session_*.json"), reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append({
                    "file":          path.name,
                    "date":          path.stem.replace("session_", ""),
                    "message_count": len(data),
                })
            except Exception:
                continue
        return sessions

    def search(self, query: str) -> list[dict]:
        """Simple full-text search across all sessions."""
        query_lower = query.lower()
        results = []
        for path in HISTORY_DIR.glob("session_*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for msg in data:
                    if query_lower in msg.get("message", "").lower():
                        results.append(msg)
            except Exception:
                continue
        return results

    def load_session_file(self, filename: str) -> list[dict]:
        """Load all messages from a specific session file."""
        path = HISTORY_DIR / filename
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def clear_all(self):
        """Delete all history files."""
        for path in HISTORY_DIR.glob("session_*.json"):
            try:
                path.unlink()
            except Exception:
                pass
        self._messages.clear()
