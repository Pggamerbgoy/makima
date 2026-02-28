"""
systems/macros.py
Record and replay keyboard/mouse macros.
"""

import os
import json
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger("Makima.Macros")

MACROS_DIR = "macros"

try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Controller as KBController, Key
    from pynput.mouse import Controller as MouseController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class MacroSystem:

    def __init__(self):
        os.makedirs(MACROS_DIR, exist_ok=True)
        self._recording = False
        self._current_macro_name: Optional[str] = None
        self._events: list[dict] = []
        self._listeners = []
        self._start_time = 0.0

    def _macro_path(self, name: str) -> str:
        return os.path.join(MACROS_DIR, f"{name.replace(' ', '_')}.json")

    def start_recording(self, name: str) -> str:
        if not PYNPUT_AVAILABLE:
            return "pynput not installed. Macros unavailable."
        if self._recording:
            return "Already recording a macro."

        self._recording = True
        self._current_macro_name = name
        self._events = []
        self._start_time = time.time()

        def on_key_press(key):
            if not self._recording:
                return False
            try:
                char = key.char
            except AttributeError:
                char = str(key)
            self._events.append({
                "type": "key_press",
                "key": char,
                "time": time.time() - self._start_time,
            })

        def on_key_release(key):
            if not self._recording:
                return False

        kb_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
        kb_listener.start()
        self._listeners = [kb_listener]
        return f"Recording macro '{name}'. Say 'stop recording' when done."

    def stop_recording(self) -> str:
        if not self._recording:
            return "No macro is being recorded."
        self._recording = False
        for listener in self._listeners:
            listener.stop()
        self._listeners = []

        name = self._current_macro_name
        path = self._macro_path(name)
        with open(path, "w") as f:
            json.dump({"name": name, "events": self._events}, f, indent=2)
        return f"Macro '{name}' saved with {len(self._events)} actions."

    def run_macro(self, name: str) -> str:
        if not PYNPUT_AVAILABLE:
            return "pynput not installed. Macros unavailable."

        path = self._macro_path(name)
        if not os.path.exists(path):
            return f"Macro '{name}' not found."

        with open(path) as f:
            data = json.load(f)

        events = data.get("events", [])
        kb = KBController()
        prev_time = 0.0

        for event in events:
            delay = event["time"] - prev_time
            if delay > 0:
                time.sleep(delay)
            prev_time = event["time"]

            if event["type"] == "key_press":
                try:
                    kb.press(event["key"])
                    kb.release(event["key"])
                except Exception:
                    pass

        return f"Macro '{name}' executed."

    def list_macros(self) -> str:
        if not os.path.isdir(MACROS_DIR):
            return "No macros saved."
        macros = [f[:-5] for f in os.listdir(MACROS_DIR) if f.endswith(".json")]
        if not macros:
            return "No macros saved yet."
        return "Saved macros: " + ", ".join(macros) + "."
