"""
systems/shortcuts.py

Conversation Shortcuts
───────────────────────
Teach Makima your own custom trigger phrases:
  - Map short phrases to full commands
  - Chain multiple commands together
  - Personal aliases for anything
  - Import/export shortcut sets

Commands:
  "Teach: wfh = start focus, open slack, open notion"
  "Shortcut: gm = good morning briefing"
  "Delete shortcut: wfh"
  "List shortcuts"
  "Run shortcut: wfh"

Examples:
  "wfh"        → opens Slack, Notion, enables focus mode
  "gm"         → full morning briefing
  "standup"    → opens Zoom + daily notes
  "code mode"  → opens VS Code, closes browser, starts focus
"""

import os
import re
import json
import logging
from typing import Optional

logger = logging.getLogger("Makima.Shortcuts")

SHORTCUTS_FILE = "shortcuts.json"

# Built-in starter shortcuts
DEFAULT_SHORTCUTS = {
    "gm": "morning briefing",
    "wfh": "start focus",
    "goodnight": "lock pc",
    "status check": "status",
}


class ShortcutSystem:
    """Maps custom phrases to commands or command chains."""

    def __init__(self, router):
        self.router = router
        self.shortcuts: dict[str, str | list] = self._load()

    def _load(self) -> dict:
        if os.path.exists(SHORTCUTS_FILE):
            try:
                with open(SHORTCUTS_FILE) as f:
                    data = json.load(f)
                    return {**DEFAULT_SHORTCUTS, **data}
            except Exception:
                pass
        return dict(DEFAULT_SHORTCUTS)

    def _save(self):
        with open(SHORTCUTS_FILE, "w") as f:
            json.dump(self.shortcuts, f, indent=2, ensure_ascii=False)

    # ── Teaching ──────────────────────────────────────────────────────────────

    def teach(self, phrase: str, command: str) -> str:
        """Add or update a shortcut."""
        phrase = phrase.strip().lower()
        command = command.strip()

        # Support chained commands: "cmd1, cmd2, cmd3"
        if "," in command:
            cmds = [c.strip() for c in command.split(",") if c.strip()]
            self.shortcuts[phrase] = cmds
            self._save()
            chain_str = " → ".join(cmds)
            return f"Shortcut saved! '{phrase}' will now run: {chain_str}"
        else:
            self.shortcuts[phrase] = command
            self._save()
            return f"Got it! '{phrase}' = '{command}'. Try saying it anytime."

    def delete(self, phrase: str) -> str:
        phrase = phrase.strip().lower()
        if phrase in self.shortcuts:
            del self.shortcuts[phrase]
            self._save()
            return f"Shortcut '{phrase}' deleted."
        return f"No shortcut found for '{phrase}'."

    # ── Running ───────────────────────────────────────────────────────────────

    def try_run(self, user_input: str) -> Optional[str]:
        """Check if input matches a shortcut. Returns combined response or None."""
        text = user_input.strip().lower()

        # Exact match
        if text in self.shortcuts:
            return self._execute(text)

        # Partial match (starts with shortcut)
        for phrase in sorted(self.shortcuts.keys(), key=len, reverse=True):
            if text.startswith(phrase):
                return self._execute(phrase)

        return None

    def _execute(self, phrase: str) -> str:
        command = self.shortcuts[phrase]
        if isinstance(command, list):
            results = []
            for cmd in command:
                result = self.router.route(cmd)
                if result:
                    results.append(result)
            return " | ".join(results) if results else f"Ran shortcut: {phrase}"
        else:
            result = self.router.route(command)
            return result or f"Ran shortcut: {phrase}"

    # ── Management ────────────────────────────────────────────────────────────

    def list_all(self) -> str:
        if not self.shortcuts:
            return "No shortcuts defined. Teach me one: 'Teach: [phrase] = [command]'"
        lines = ["Your shortcuts:"]
        for phrase, command in sorted(self.shortcuts.items()):
            cmd_str = " → ".join(command) if isinstance(command, list) else command
            lines.append(f"  '{phrase}' → {cmd_str}")
        return "\n".join(lines)

    def suggest(self, usage_log: list[str]) -> str:
        """AI-powered shortcut suggestions based on command history."""
        if len(usage_log) < 5:
            return "Use Makima more and I'll suggest useful shortcuts!"
        common = {}
        for cmd in usage_log:
            common[cmd] = common.get(cmd, 0) + 1
        top = sorted(common.items(), key=lambda x: x[1], reverse=True)[:5]
        suggestions = [f"  '{cmd}' (used {n}x)" for cmd, n in top]
        return "Frequent commands you could shortcut:\n" + "\n".join(suggestions)

    def export(self, path: str) -> str:
        try:
            with open(path, "w") as f:
                json.dump(self.shortcuts, f, indent=2)
            return f"Shortcuts exported to {path}."
        except Exception as e:
            return f"Export failed: {e}"

    def import_file(self, path: str) -> str:
        try:
            with open(path) as f:
                data = json.load(f)
            self.shortcuts.update(data)
            self._save()
            return f"Imported {len(data)} shortcuts."
        except Exception as e:
            return f"Import failed: {e}"
