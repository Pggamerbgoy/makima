"""
systems/hotkey_manager.py

Hotkey Activation System
─────────────────────────
Press a key combo instead of saying "Hey Makima":
  - Default: Ctrl+Space → start listening immediately
  - Configurable to any key combination
  - Double-tap Ctrl → quick command mode
  - Hold key → push-to-talk mode
  - Visual feedback on HUD when activated
  - Works system-wide (even when Makima window not focused)

Commands:
  "Set hotkey to Ctrl+Shift+M"
  "Change activation key"
  "Disable hotkey"
  "Push to talk mode"
  "What's my hotkey?"

Install: pip install keyboard
"""

import os
import json
import time
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger("Makima.HotkeyManager")

HOTKEY_CONFIG_FILE = "hotkey_config.json"

DEFAULT_CONFIG = {
    "activation_hotkey": "ctrl+space",
    "push_to_talk_key": "ctrl+shift+space",
    "quick_command_hotkey": "ctrl+ctrl",   # double-tap ctrl
    "enabled": True,
    "mode": "tap",                          # "tap" | "hold" (push-to-talk)
    "feedback_sound": True,
}

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    logger.warning("keyboard library not installed. Hotkeys disabled.")
    logger.warning("Install: pip install keyboard (may need admin/sudo)")


class HotkeyManager:
    """
    Global hotkey system for activating Makima without wake word.
    Runs in background, fires callback when hotkey pressed.
    """

    def __init__(self,
                 on_activate: Callable,           # Called when hotkey pressed → start listening
                 on_push_to_talk_start: Callable = None,
                 on_push_to_talk_end: Callable = None):
        self.on_activate = on_activate
        self.on_ptt_start = on_push_to_talk_start
        self.on_ptt_end = on_push_to_talk_end
        self.config = self._load_config()
        self._registered = []
        self._ptt_active = False
        self._ctrl_timestamps = []  # For double-tap detection
        self._running = False

    def _load_config(self) -> dict:
        if os.path.exists(HOTKEY_CONFIG_FILE):
            try:
                with open(HOTKEY_CONFIG_FILE) as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def _save_config(self):
        with open(HOTKEY_CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    # ── Registration ──────────────────────────────────────────────────────────

    def start(self):
        if not KEYBOARD_AVAILABLE:
            logger.warning("Hotkey system unavailable (keyboard not installed).")
            return
        if not self.config.get("enabled", True):
            return

        self._running = True
        self._register_hotkeys()
        logger.info(
            f"⌨️  Hotkey active: [{self.config['activation_hotkey']}] → activate Makima"
        )

    def _register_hotkeys(self):
        if not KEYBOARD_AVAILABLE:
            return

        # Clear previous registrations
        for h in self._registered:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self._registered = []

        mode = self.config.get("mode", "tap")
        hotkey = self.config.get("activation_hotkey", "ctrl+space")

        if mode == "tap":
            h = keyboard.add_hotkey(hotkey, self._on_tap_activate, suppress=False)
            self._registered.append(h)
        elif mode == "hold":
            # Push-to-talk
            key = self.config.get("push_to_talk_key", "ctrl+shift+space")
            keyboard.on_press_key(key.split("+")[-1], self._on_ptt_press)
            keyboard.on_release_key(key.split("+")[-1], self._on_ptt_release)

        logger.info(f"Registered hotkey: {hotkey} (mode: {mode})")

    def _on_tap_activate(self):
        """Called when activation hotkey is tapped."""
        logger.debug("Hotkey activated!")
        threading.Thread(target=self.on_activate, daemon=True).start()

    def _on_ptt_press(self, event):
        if not self._ptt_active:
            self._ptt_active = True
            if self.on_ptt_start:
                threading.Thread(target=self.on_ptt_start, daemon=True).start()

    def _on_ptt_release(self, event):
        if self._ptt_active:
            self._ptt_active = False
            if self.on_ptt_end:
                threading.Thread(target=self.on_ptt_end, daemon=True).start()

    def stop(self):
        self._running = False
        if KEYBOARD_AVAILABLE:
            keyboard.unhook_all_hotkeys()
        logger.info("Hotkeys unregistered.")

    # ── Configuration ─────────────────────────────────────────────────────────

    def set_hotkey(self, combo: str) -> str:
        """Set a new activation hotkey."""
        if not KEYBOARD_AVAILABLE:
            return "keyboard library not installed."

        # Validate combo
        combo = combo.lower().strip().replace(" ", "+")
        try:
            # Test if valid
            test = keyboard.add_hotkey(combo, lambda: None)
            keyboard.remove_hotkey(test)
        except Exception as e:
            return f"Invalid hotkey '{combo}': {e}"

        self.config["activation_hotkey"] = combo
        self._save_config()
        self._register_hotkeys()
        return f"Activation hotkey set to [{combo.upper()}]. Press it to activate me!"

    def set_mode_tap(self) -> str:
        self.config["mode"] = "tap"
        self._save_config()
        self._register_hotkeys()
        return f"Tap mode: press [{self.config['activation_hotkey'].upper()}] once to activate."

    def set_mode_ptt(self) -> str:
        self.config["mode"] = "hold"
        self._save_config()
        self._register_hotkeys()
        key = self.config.get("push_to_talk_key", "ctrl+shift+space")
        return f"Push-to-talk mode: hold [{key.upper()}] while speaking."

    def disable(self) -> str:
        self.config["enabled"] = False
        self._save_config()
        self.stop()
        return "Hotkey activation disabled. Use wake word 'Hey Makima' instead."

    def enable(self) -> str:
        self.config["enabled"] = True
        self._save_config()
        self.start()
        return f"Hotkey activation enabled: [{self.config['activation_hotkey'].upper()}]"

    def get_status(self) -> str:
        if not KEYBOARD_AVAILABLE:
            return "Hotkeys unavailable (install: pip install keyboard)"
        status = "enabled" if self.config.get("enabled") else "disabled"
        return (
            f"Hotkey: {status}. "
            f"Activation: [{self.config['activation_hotkey'].upper()}]. "
            f"Mode: {self.config['mode']}."
        )
