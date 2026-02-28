"""
systems/overlay.py
Transparent on-screen overlay that shows Makima's spoken text.
Uses tkinter (no extra deps). Runs in its own thread.
"""

import threading
import logging

logger = logging.getLogger("Makima.Overlay")

try:
    import tkinter as tk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False


class Overlay:
    """Semi-transparent always-on-top overlay for displaying Makima's responses."""

    def __init__(self):
        self._text = ""
        self._root = None
        self._label = None
        self._thread = None
        if TK_AVAILABLE:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        else:
            logger.warning("tkinter not available. Overlay disabled.")

    def _run(self):
        try:
            self._root = tk.Tk()
            self._root.title("Makima")
            self._root.overrideredirect(True)  # No window border
            self._root.attributes("-topmost", True)
            self._root.attributes("-alpha", 0.85)
            self._root.configure(bg="#0a0a0f")

            # Position at bottom center
            screen_w = self._root.winfo_screenwidth()
            screen_h = self._root.winfo_screenheight()
            width, height = 700, 60
            x = (screen_w - width) // 2
            y = screen_h - height - 40
            self._root.geometry(f"{width}x{height}+{x}+{y}")

            self._label = tk.Label(
                self._root,
                text="",
                font=("Segoe UI", 14),
                fg="#c084fc",
                bg="#0a0a0f",
                wraplength=680,
                justify="center",
            )
            self._label.pack(expand=True, fill="both", padx=10)

            self._root.mainloop()
        except Exception as e:
            logger.warning(f"Overlay error: {e}")

    def show(self, text: str, duration_ms: int = 5000):
        """Show text on overlay for duration_ms milliseconds."""
        if not self._root or not self._label:
            return
        try:
            self._root.after(0, self._update_text, text)
            self._root.after(duration_ms, self._clear_text)
        except Exception:
            pass

    def _update_text(self, text: str):
        if self._label:
            self._label.config(text=text)

    def _clear_text(self):
        if self._label:
            self._label.config(text="")
