"""
ui/hud.py

Makima HUD — Complete Visual Interface
────────────────────────────────────────
Three integrated visual components:

1. MINI HUD (always-on corner widget)
   - Time, date, battery, weather icon
   - Makima status (listening / thinking / speaking / idle)
   - Latest response preview
   - Emotion indicator
   - Hotkey hint

2. ANIMATED AVATAR
   - Animated circle that reacts to states
   - Pulses when listening
   - Glows when speaking
   - Breathes when idle
   - Changes color with emotion
   - Lip-sync animation (amplitude-driven)

3. VOICE WAVEFORM VISUALIZER
   - Real-time audio input bars
   - Shows when Makima is listening
   - Animates during speech output

All three are embedded in one transparent tkinter overlay.
Toggle with: "Show HUD" / "Hide HUD" / "Toggle HUD"
"""

import time
import math
import threading
import logging
import platform
from typing import Optional, Callable

logger = logging.getLogger("Makima.HUD")
OS = platform.system()

try:
    import tkinter as tk
    from tkinter import ttk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# ── Color Palette ─────────────────────────────────────────────────────────────
COLORS = {
    "bg":           "#0a0a12",
    "bg_secondary": "#12121e",
    "border":       "#1e1e32",
    "text":         "#e0d4f7",
    "text_dim":     "#6b6b8a",
    "accent":       "#c084fc",       # Purple — Makima's color
    "accent_glow":  "#a855f7",
    "green":        "#4ade80",
    "yellow":       "#fbbf24",
    "red":          "#f87171",
    "blue":         "#60a5fa",
    "idle":         "#6366f1",
    "listening":    "#22c55e",
    "thinking":     "#f59e0b",
    "speaking":     "#c084fc",
    "error":        "#ef4444",
}

EMOTION_COLORS = {
    "happy":   "#fbbf24",
    "excited": "#f97316",
    "sad":     "#60a5fa",
    "angry":   "#ef4444",
    "stressed":"#f59e0b",
    "calm":    "#4ade80",
    "tired":   "#6b6b8a",
    "neutral": "#c084fc",
}

STATUS_LABELS = {
    "idle":      "Idle",
    "listening": "Listening...",
    "thinking":  "Thinking...",
    "speaking":  "Speaking",
    "error":     "Error",
}


class MakimaHUD:
    """
    Full transparent HUD overlay with avatar, waveform, and status info.
    Runs in its own thread — completely non-blocking.
    """

    HUD_WIDTH  = 320
    HUD_HEIGHT = 200
    AVATAR_SIZE = 80
    WAVEFORM_BARS = 20

    def __init__(self):
        # State
        self.status = "idle"
        self.emotion = "neutral"
        self.latest_text = ""
        self.audio_levels: list[float] = [0.0] * self.WAVEFORM_BARS
        self.visible = True
        self._running = False
        self._minimized = False

        # Tkinter refs
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._avatar_items = []
        self._waveform_items = []

        # Animation state
        self._anim_tick = 0
        self._speaking_amplitude = 0.0
        self._pulse_phase = 0.0

        if TK_AVAILABLE:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        else:
            logger.warning("tkinter not available. HUD disabled.")

    # ── Window Setup ──────────────────────────────────────────────────────────

    def _run(self):
        try:
            self._root = tk.Tk()
            self._root.title("Makima HUD")
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)
            self._root.attributes("-alpha", 0.92)
            self._root.configure(bg=COLORS["bg"])

            if OS == "Windows":
                self._root.attributes("-transparentcolor", "")
            elif OS == "Darwin":
                self._root.attributes("-transparent", True)

            # Position bottom-right
            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            x = sw - self.HUD_WIDTH - 20
            y = sh - self.HUD_HEIGHT - 50
            self._root.geometry(f"{self.HUD_WIDTH}x{self.HUD_HEIGHT}+{x}+{y}")

            # Canvas
            self._canvas = tk.Canvas(
                self._root,
                width=self.HUD_WIDTH,
                height=self.HUD_HEIGHT,
                bg=COLORS["bg"],
                highlightthickness=0,
            )
            self._canvas.pack()

            # Drag to move
            self._canvas.bind("<ButtonPress-1>", self._drag_start)
            self._canvas.bind("<B1-Motion>", self._drag_move)
            self._canvas.bind("<Double-Button-1>", lambda e: self.toggle_minimized())

            self._draw_static()
            self._animate()
            self._root.mainloop()
        except Exception as e:
            logger.warning(f"HUD error: {e}")

    def _drag_start(self, event):
        self._root._drag_x = event.x
        self._root._drag_y = event.y

    def _drag_move(self, event):
        dx = event.x - self._root._drag_x
        dy = event.y - self._root._drag_y
        x = self._root.winfo_x() + dx
        y = self._root.winfo_y() + dy
        self._root.geometry(f"+{x}+{y}")

    # ── Static Layout ─────────────────────────────────────────────────────────

    def _draw_static(self):
        c = self._canvas
        W, H = self.HUD_WIDTH, self.HUD_HEIGHT

        # Rounded border
        c.create_rectangle(2, 2, W-2, H-2, outline=COLORS["border"],
                           width=1, fill=COLORS["bg_secondary"])

        # Title bar line
        c.create_line(16, 28, W-16, 28, fill=COLORS["border"], width=1)

        # "MAKIMA" label
        c.create_text(W//2, 15, text="M A K I M A",
                     font=("Segoe UI", 8, "bold"), fill=COLORS["accent"])

        # Minimize button hint
        c.create_text(W-15, 15, text="×", font=("Segoe UI", 10),
                     fill=COLORS["text_dim"])

    # ── Animation Loop ────────────────────────────────────────────────────────

    def _animate(self):
        if not self._root or not self._canvas:
            return
        try:
            self._anim_tick += 1
            self._pulse_phase += 0.08
            if self._pulse_phase > 2 * math.pi:
                self._pulse_phase = 0

            self._redraw()
            self._root.after(50, self._animate)  # 20 FPS
        except Exception:
            pass

    def _redraw(self):
        c = self._canvas
        W, H = self.HUD_WIDTH, self.HUD_HEIGHT
        # Clear dynamic area
        c.delete("dynamic")

        # ── Avatar (left side) ────────────────────────────────────────────────
        ax, ay = 55, 100  # center
        self._draw_avatar(ax, ay)

        # ── Status + Text (right side) ────────────────────────────────────────
        text_x = 115

        # Status dot + label
        status_color = COLORS.get(self.status, COLORS["idle"])
        c.create_oval(text_x, 38, text_x+8, 46,
                     fill=status_color, outline="", tags="dynamic")
        c.create_text(text_x+14, 42, text=STATUS_LABELS.get(self.status, self.status),
                     font=("Segoe UI", 8, "bold"), fill=status_color,
                     anchor="w", tags="dynamic")

        # Emotion indicator
        emotion_color = EMOTION_COLORS.get(self.emotion, COLORS["accent"])
        c.create_text(text_x, 60, text=f"Mood: {self.emotion.title()}",
                     font=("Segoe UI", 7), fill=emotion_color,
                     anchor="w", tags="dynamic")

        # System info
        self._draw_system_info(text_x, 78)

        # Latest response preview
        if self.latest_text:
            preview = self.latest_text[:45] + "…" if len(self.latest_text) > 45 else self.latest_text
            c.create_text(text_x, 120, text=preview,
                         font=("Segoe UI", 7), fill=COLORS["text"],
                         anchor="w", width=190, tags="dynamic")

        # ── Waveform (bottom) ─────────────────────────────────────────────────
        self._draw_waveform(16, H-30, W-32, 20)

        # ── Time ──────────────────────────────────────────────────────────────
        time_str = time.strftime("%H:%M:%S")
        c.create_text(W-16, 15, text=time_str,
                     font=("Segoe UI", 8), fill=COLORS["text_dim"],
                     anchor="e", tags="dynamic")

    def _draw_avatar(self, cx: int, cy: int):
        c = self._canvas
        t = self._pulse_phase
        status = self.status
        emotion_color = EMOTION_COLORS.get(self.emotion, COLORS["accent"])

        # Outer glow ring
        if status == "listening":
            # Pulsing green ring
            r_outer = 36 + 4 * math.sin(t * 2)
            alpha_ring = int(180 + 60 * math.sin(t * 2))
            c.create_oval(cx-r_outer, cy-r_outer, cx+r_outer, cy+r_outer,
                         outline=COLORS["listening"], width=2, tags="dynamic")

        elif status == "speaking":
            # Expanding rings (ripple)
            for i in range(3):
                phase = (t + i * 0.7) % (2 * math.pi)
                r = 32 + 20 * (phase / (2 * math.pi))
                alpha = int(255 * (1 - phase / (2 * math.pi)))
                c.create_oval(cx-r, cy-r, cx+r, cy+r,
                             outline=COLORS["speaking"], width=1, tags="dynamic")

        elif status == "thinking":
            # Rotating dashed ring
            for i in range(8):
                angle = t + i * math.pi / 4
                r = 36
                x1 = cx + r * math.cos(angle) - 2
                y1 = cy + r * math.sin(angle) - 2
                x2 = x1 + 4
                y2 = y1 + 4
                c.create_oval(x1, y1, x2, y2,
                             fill=COLORS["thinking"], outline="", tags="dynamic")

        else:
            # Idle: slow breathing circle
            r_outer = 34 + 2 * math.sin(t * 0.5)
            c.create_oval(cx-r_outer, cy-r_outer, cx+r_outer, cy+r_outer,
                         outline=COLORS["idle"], width=1, tags="dynamic")

        # Core circle (avatar body)
        r_core = 28
        if status == "speaking":
            r_core = 28 + 4 * math.sin(t * 4) * self._speaking_amplitude
        c.create_oval(cx-r_core, cy-r_core, cx+r_core, cy+r_core,
                     fill=COLORS["bg_secondary"], outline=emotion_color,
                     width=2, tags="dynamic")

        # "M" letter inside
        c.create_text(cx, cy, text="M", font=("Segoe UI", 16, "bold"),
                     fill=emotion_color, tags="dynamic")

    def _draw_waveform(self, x: int, y: int, width: int, height: int):
        c = self._canvas
        bars = self.WAVEFORM_BARS
        bar_w = (width - bars) // bars
        status = self.status

        for i in range(bars):
            if status == "listening":
                # Use real audio level + animation
                level = self.audio_levels[i] if i < len(self.audio_levels) else 0
                h = max(2, int(height * (0.2 + 0.8 * level)))
            elif status == "speaking":
                # Smooth wave during speech
                phase = self._pulse_phase + i * 0.4
                h = max(2, int(height * 0.4 * abs(math.sin(phase)) +
                              height * 0.2 * self._speaking_amplitude))
            elif status == "thinking":
                # Slow ripple
                phase = self._pulse_phase * 0.5 + i * 0.3
                h = max(2, int(height * 0.3 * abs(math.sin(phase))))
            else:
                # Idle: tiny baseline
                h = max(2, int(height * 0.05 * (1 + math.sin(self._pulse_phase + i * 0.5))))

            bar_x = x + i * (bar_w + 1)
            bar_color = COLORS.get(status, COLORS["idle"])
            c.create_rectangle(
                bar_x, y + height - h,
                bar_x + bar_w, y + height,
                fill=bar_color, outline="", tags="dynamic"
            )

    def _draw_system_info(self, x: int, y: int):
        c = self._canvas
        parts = []
        if PSUTIL_AVAILABLE:
            try:
                batt = psutil.sensors_battery()
                if batt:
                    icon = "🔌" if batt.power_plugged else "🔋"
                    color = COLORS["green"] if batt.percent > 30 else COLORS["red"]
                    c.create_text(x, y, text=f"{icon} {batt.percent:.0f}%",
                                 font=("Segoe UI", 7), fill=color,
                                 anchor="w", tags="dynamic")
                    y += 14

                cpu = psutil.cpu_percent()
                cpu_color = COLORS["red"] if cpu > 80 else COLORS["text_dim"]
                c.create_text(x, y, text=f"CPU {cpu:.0f}%",
                             font=("Segoe UI", 7), fill=cpu_color,
                             anchor="w", tags="dynamic")
            except Exception:
                pass

    # ── Toggle ────────────────────────────────────────────────────────────────

    def toggle_minimized(self):
        if not self._root:
            return
        if self._minimized:
            self._root.geometry(f"{self.HUD_WIDTH}x{self.HUD_HEIGHT}")
            self._minimized = False
        else:
            self._root.geometry(f"{self.HUD_WIDTH}x32")
            self._minimized = True

    def show(self):
        if self._root:
            self._root.deiconify()
            self.visible = True

    def hide(self):
        if self._root:
            self._root.withdraw()
            self.visible = False

    # ── State Updates (thread-safe) ───────────────────────────────────────────

    def set_status(self, status: str):
        self.status = status
        if status != "speaking":
            self._speaking_amplitude = 0.0

    def set_emotion(self, emotion: str):
        self.emotion = emotion

    def set_text(self, text: str):
        self.latest_text = text

    def set_audio_levels(self, levels: list[float]):
        """Update waveform bars with real audio amplitude data."""
        self.audio_levels = levels[:self.WAVEFORM_BARS]
        if levels:
            self._speaking_amplitude = max(levels)

    def update_all(self, status: str = None, emotion: str = None,
                   text: str = None, audio_levels: list = None):
        if status:
            self.set_status(status)
        if emotion:
            self.set_emotion(emotion)
        if text is not None:
            self.set_text(text)
        if audio_levels is not None:
            self.set_audio_levels(audio_levels)
