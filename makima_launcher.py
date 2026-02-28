"""
Makima Launcher
───────────────────────────────────────────
Desktop start/stop UI for Makima assistant.
Pure tkinter — no extra installs needed.

Place this file in your project root (same
folder as makima_assistant.py) and run:
    python makima_launcher.py
"""

import tkinter as tk
from tkinter import font as tkfont
import subprocess
import threading
import sys
import os
import time
import psutil
from datetime import datetime
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

MAKIMA_SCRIPT   = "makima_assistant.py"   # your main script
MAKIMA_TITLE    = "MAKIMA"
VERSION         = "v4.0"
PYTHON          = sys.executable          # same python that runs this launcher

# Colors — matches the HTML UI exactly
C = {
    "void":         "#06050a",
    "deep":         "#0d0b14",
    "surface":      "#13101d",
    "lift":         "#1c1829",
    "border":       "#1e1a2e",
    "border_lit":   "#3d2e5a",
    "crimson":      "#e63560",
    "crimson_dim":  "#2a0f18",
    "violet":       "#b482ff",
    "violet_dim":   "#1a1030",
    "ice":          "#7fd4f7",
    "green":        "#3dcc78",
    "green_dim":    "#0d2018",
    "text":         "#f0ecf8",
    "muted":        "#6b6380",
    "faint":        "#3a3449",
}

# ── STATE ─────────────────────────────────────────────────────────────────────

class MakimaState:
    OFFLINE  = "OFFLINE"
    STARTING = "STARTING"
    ONLINE   = "ONLINE"
    STOPPING = "STOPPING"


# ── MAIN WINDOW ───────────────────────────────────────────────────────────────

class MakimaLauncher(tk.Tk):

    def __init__(self):
        super().__init__()

        self.state_var   = MakimaState.OFFLINE
        self.process     = None
        self.log_lines   = []
        self.uptime_start = None
        self._uptime_job  = None

        self._build_window()
        self._build_fonts()
        self._build_ui()
        self._start_clock()
        self._refresh_status()

        # Check if already running on open
        self.after(300, self._check_already_running)

    # ── WINDOW SETUP ─────────────────────────────────────────────────────────

    def _build_window(self):
        self.title("Makima Launcher")
        self.configure(bg=C["void"])
        self.resizable(False, False)

        # Center on screen
        w, h = 820, 580
        self.geometry(f"{w}x{h}")
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Remove default titlebar on Windows, keep on others
        try:
            self.overrideredirect(True)
            self._drag_x = 0
            self._drag_y = 0
        except Exception:
            pass

    def _build_fonts(self):
        self.f_title  = tkfont.Font(family="Segoe UI",       size=22, weight="bold")
        self.f_sub    = tkfont.Font(family="Segoe UI",       size=8,  weight="normal")
        self.f_label  = tkfont.Font(family="Segoe UI",       size=9,  weight="bold")
        self.f_mono   = tkfont.Font(family="Courier New",    size=8,  weight="normal")
        self.f_mono_b = tkfont.Font(family="Courier New",    size=8,  weight="bold")
        self.f_status = tkfont.Font(family="Segoe UI",       size=10, weight="bold")
        self.f_btn    = tkfont.Font(family="Segoe UI",       size=10, weight="bold")
        self.f_small  = tkfont.Font(family="Courier New",    size=7)
        self.f_stat   = tkfont.Font(family="Segoe UI",       size=16, weight="bold")

    # ── UI BUILD ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Custom titlebar ───────────────────────────────────────────────────
        self.titlebar = tk.Frame(self, bg=C["deep"], height=40)
        self.titlebar.pack(fill="x", side="top")
        self.titlebar.pack_propagate(False)

        # Drag support
        self.titlebar.bind("<ButtonPress-1>",   self._drag_start)
        self.titlebar.bind("<B1-Motion>",       self._drag_move)

        tk.Label(self.titlebar, text="◈  MAKIMA LAUNCHER",
                 font=self.f_label, bg=C["deep"], fg=C["muted"],
                 padx=16).pack(side="left", pady=10)

        # Clock
        self.clock_lbl = tk.Label(self.titlebar, text="",
                                   font=self.f_small, bg=C["deep"], fg=C["faint"])
        self.clock_lbl.pack(side="left", padx=4)

        # Window controls
        btn_frame = tk.Frame(self.titlebar, bg=C["deep"])
        btn_frame.pack(side="right", padx=12)

        self._win_btn(btn_frame, "−", C["muted"],   self.iconify)
        self._win_btn(btn_frame, "×", C["crimson"],  self._on_close)

        # ── Body ──────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=C["void"])
        body.pack(fill="both", expand=True, padx=0, pady=0)

        # Left sidebar (72px — same as HTML UI)
        sidebar = tk.Frame(body, bg=C["deep"], width=72)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._build_sidebar(sidebar)

        # Main content area
        main = tk.Frame(body, bg=C["void"])
        main.pack(side="left", fill="both", expand=True)
        self._build_main(main)

        # Right info panel (280px)
        right = tk.Frame(body, bg=C["deep"], width=280)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self._build_right(right)

    def _win_btn(self, parent, text, fg, cmd):
        btn = tk.Label(parent, text=text, font=self.f_label,
                       bg=C["deep"], fg=fg, cursor="hand2", padx=8)
        btn.pack(side="left")
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>",    lambda e: btn.config(bg=C["lift"]))
        btn.bind("<Leave>",    lambda e: btn.config(bg=C["deep"]))

    # ── SIDEBAR ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        # Logo mark
        logo = tk.Label(parent, text="◈", font=tkfont.Font(size=18, weight="bold"),
                        bg=C["deep"], fg=C["crimson"])
        logo.pack(pady=(20, 24))

        # Nav icons (unicode symbols as nav items)
        nav_items = [
            ("⌂", "Home",     True),
            ("⚙", "Settings", False),
            ("◉", "Modules",  False),
            ("⊞", "Logs",     False),
        ]
        for icon, tip, active in nav_items:
            fg  = C["crimson"] if active else C["muted"]
            bg  = C["crimson_dim"] if active else C["deep"]
            btn = tk.Label(parent, text=icon,
                           font=tkfont.Font(size=14),
                           bg=bg, fg=fg,
                           width=3, pady=10, cursor="hand2")
            btn.pack(fill="x", padx=10, pady=2)
            if not active:
                btn.bind("<Enter>", lambda e, b=btn: b.config(bg=C["lift"], fg=C["text"]))
                btn.bind("<Leave>", lambda e, b=btn: b.config(bg=C["deep"], fg=C["muted"]))

        # Version at bottom
        tk.Label(parent, text=VERSION, font=self.f_small,
                 bg=C["deep"], fg=C["faint"]).pack(side="bottom", pady=16)

    # ── MAIN PANEL ───────────────────────────────────────────────────────────

    def _build_main(self, parent):

        # ── Top section: title + status ───────────────────────────────────────
        top = tk.Frame(parent, bg=C["void"])
        top.pack(fill="x", padx=32, pady=(28, 0))

        # Title row
        title_row = tk.Frame(top, bg=C["void"])
        title_row.pack(fill="x")

        tk.Label(title_row, text=MAKIMA_TITLE,
                 font=self.f_title, bg=C["void"], fg=C["text"]).pack(side="left")

        self.status_pill = tk.Label(title_row, text="  ●  OFFLINE  ",
                                    font=self.f_small,
                                    bg=C["crimson_dim"], fg=C["crimson"],
                                    padx=10, pady=4)
        self.status_pill.pack(side="left", padx=(16, 0), pady=8)

        tk.Label(top, text="AI ASSISTANT  ·  " + VERSION,
                 font=self.f_small, bg=C["void"], fg=C["muted"]).pack(anchor="w")

        # Divider
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=32, pady=(16, 0))

        # ── Center: main control orb ──────────────────────────────────────────
        center = tk.Frame(parent, bg=C["void"])
        center.pack(fill="both", expand=True, padx=32)

        orb_frame = tk.Frame(center, bg=C["void"])
        orb_frame.place(relx=0.5, rely=0.42, anchor="center")

        # Outer ring (canvas-drawn circles)
        self.orb_canvas = tk.Canvas(orb_frame, width=200, height=200,
                                    bg=C["void"], highlightthickness=0)
        self.orb_canvas.pack()

        self._draw_orb(MakimaState.OFFLINE)

        # State label under orb
        self.state_lbl = tk.Label(orb_frame, text="OFFLINE",
                                   font=self.f_label,
                                   bg=C["void"], fg=C["muted"],
                                   pady=4)
        self.state_lbl.pack()

        self.uptime_lbl = tk.Label(orb_frame, text="",
                                    font=self.f_small,
                                    bg=C["void"], fg=C["faint"])
        self.uptime_lbl.pack()

        # ── Bottom: action buttons ────────────────────────────────────────────
        btn_row = tk.Frame(parent, bg=C["void"])
        btn_row.pack(fill="x", padx=32, pady=(0, 24))

        self.start_btn = self._action_btn(btn_row, "▶  START MAKIMA",
                                          C["crimson"], C["void"],
                                          self._start_makima)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.stop_btn = self._action_btn(btn_row, "■  STOP",
                                          C["surface"], C["muted"],
                                          self._stop_makima)
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(8, 8))

        self.restart_btn = self._action_btn(btn_row, "↺  RESTART",
                                             C["surface"], C["muted"],
                                             self._restart_makima)
        self.restart_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _action_btn(self, parent, text, bg, fg, cmd):
        btn = tk.Label(parent, text=text,
                       font=self.f_btn,
                       bg=bg, fg=fg,
                       pady=12, cursor="hand2",
                       relief="flat")
        orig_bg = bg
        btn.bind("<Button-1>",  lambda e: cmd())
        btn.bind("<Enter>",     lambda e: btn.config(bg=self._lighten(orig_bg)))
        btn.bind("<Leave>",     lambda e: btn.config(bg=orig_bg))
        return btn

    def _lighten(self, hex_color):
        """Make a hex color slightly lighter for hover."""
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = min(255, r + 25)
            g = min(255, g + 25)
            b = min(255, b + 25)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    # ── RIGHT PANEL ───────────────────────────────────────────────────────────

    def _build_right(self, parent):
        # Header
        tk.Label(parent, text="SYSTEM STATUS",
                 font=self.f_small, bg=C["deep"], fg=C["muted"],
                 padx=20, pady=16, anchor="w").pack(fill="x")

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

        # Stat cards
        cards_frame = tk.Frame(parent, bg=C["deep"])
        cards_frame.pack(fill="x", padx=12, pady=12)

        self.stat_widgets = {}
        stats = [
            ("CPU",     "cpu",     "%",  C["violet"]),
            ("RAM",     "ram",     "%",  C["ice"]),
            ("UPTIME",  "uptime",  "",   C["green"]),
            ("PID",     "pid",     "",   C["crimson"]),
        ]
        for i, (label, key, unit, color) in enumerate(stats):
            row = i // 2
            col = i %  2
            card = tk.Frame(cards_frame, bg=C["surface"],
                            highlightbackground=C["border"],
                            highlightthickness=1)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            cards_frame.grid_columnconfigure(col, weight=1)

            tk.Label(card, text=label, font=self.f_small,
                     bg=C["surface"], fg=C["muted"],
                     pady=6, padx=10, anchor="w").pack(fill="x")

            val_lbl = tk.Label(card, text="—",
                               font=self.f_stat,
                               bg=C["surface"], fg=color,
                               pady=2, padx=10, anchor="w")
            val_lbl.pack(fill="x")
            self.stat_widgets[key] = val_lbl

            if unit:
                tk.Label(card, text=unit, font=self.f_small,
                         bg=C["surface"], fg=C["faint"],
                         pady=4, padx=10, anchor="w").pack(fill="x")
            else:
                tk.Label(card, text=" ", font=self.f_small,
                         bg=C["surface"], fg=C["faint"],
                         pady=4, padx=10, anchor="w").pack(fill="x")

        # Divider
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=(8, 0))

        # Log panel label
        tk.Label(parent, text="LIVE LOG",
                 font=self.f_small, bg=C["deep"], fg=C["muted"],
                 padx=20, pady=10, anchor="w").pack(fill="x")

        # Log text box
        log_frame = tk.Frame(parent, bg=C["deep"], padx=12, pady=0)
        log_frame.pack(fill="both", expand=True, padx=0)

        self.log_box = tk.Text(log_frame,
                               font=self.f_mono,
                               bg=C["surface"], fg=C["muted"],
                               relief="flat",
                               highlightthickness=1,
                               highlightbackground=C["border"],
                               insertbackground=C["violet"],
                               selectbackground=C["violet_dim"],
                               wrap="word",
                               state="disabled",
                               padx=8, pady=8)
        self.log_box.pack(fill="both", expand=True)

        # Log tags for coloring
        self.log_box.tag_config("info",    foreground=C["muted"])
        self.log_box.tag_config("success", foreground=C["green"])
        self.log_box.tag_config("error",   foreground=C["crimson"])
        self.log_box.tag_config("warn",    foreground="#f0c040")
        self.log_box.tag_config("dim",     foreground=C["faint"])
        self.log_box.tag_config("time",    foreground=C["faint"])
        self.log_box.tag_config("violet",  foreground=C["violet"])

        # Clear log button
        clear_btn = tk.Label(parent, text="CLEAR LOG",
                             font=self.f_small, bg=C["deep"],
                             fg=C["faint"], cursor="hand2", pady=8)
        clear_btn.pack()
        clear_btn.bind("<Button-1>", lambda e: self._clear_log())
        clear_btn.bind("<Enter>",    lambda e: clear_btn.config(fg=C["muted"]))
        clear_btn.bind("<Leave>",    lambda e: clear_btn.config(fg=C["faint"]))

    # ── ORB DRAWING ───────────────────────────────────────────────────────────

    def _draw_orb(self, state):
        c = self.orb_canvas
        c.delete("all")

        cx, cy, r = 100, 100, 100

        colors = {
            MakimaState.OFFLINE:  (C["faint"],      C["border"],     C["muted"]),
            MakimaState.STARTING: ("#f0c040",        "#2a2000",       "#f0c040"),
            MakimaState.ONLINE:   (C["green"],       C["green_dim"],  C["green"]),
            MakimaState.STOPPING: (C["crimson"],     C["crimson_dim"],C["crimson"]),
        }
        ring_color, fill_color, dot_color = colors.get(state, colors[MakimaState.OFFLINE])

        # Outer ring glow
        for i in range(4, 0, -1):
            alpha_hex = ["22", "18", "12", "08"][4-i]
            try:
                c.create_oval(cx-r+i*3, cy-r+i*3, cx+r-i*3, cy+r-i*3,
                              outline=ring_color + alpha_hex, width=1)
            except Exception:
                pass

        # Main outer ring
        c.create_oval(cx-r+10, cy-r+10, cx+r-10, cy+r-10,
                      outline=ring_color, width=1.5)

        # Middle ring
        c.create_oval(cx-r+28, cy-r+28, cx+r-28, cy+r-28,
                      outline=ring_color, width=1, dash=(4, 6))

        # Inner filled circle
        c.create_oval(cx-r+44, cy-r+44, cx+r-44, cy+r-44,
                      fill=fill_color, outline=ring_color, width=1.5)

        # Center dot
        c.create_oval(cx-8, cy-8, cx+8, cy+8,
                      fill=dot_color, outline="")

        # Animated pulse ring for ONLINE
        if state == MakimaState.ONLINE:
            c.create_oval(cx-r+36, cy-r+36, cx+r-36, cy+r-36,
                          outline=C["green"], width=1, dash=(2, 8))

        # Cross hairs for OFFLINE
        if state == MakimaState.OFFLINE:
            c.create_line(cx-20, cy, cx+20, cy, fill=C["faint"], width=1)
            c.create_line(cx, cy-20, cx, cy+20, fill=C["faint"], width=1)

        # Tick marks around ring
        import math
        for i in range(12):
            angle = math.radians(i * 30)
            r2 = r - 12
            x1 = cx + (r2-6) * math.cos(angle)
            y1 = cy + (r2-6) * math.sin(angle)
            x2 = cx + r2 * math.cos(angle)
            y2 = cy + r2 * math.sin(angle)
            tick_col = ring_color if i % 3 == 0 else C["faint"]
            c.create_line(x1, y1, x2, y2, fill=tick_col, width=1)

    # ── ACTIONS ───────────────────────────────────────────────────────────────

    def _start_makima(self):
        if self.state_var in (MakimaState.ONLINE, MakimaState.STARTING):
            self._log("Makima is already running.", "warn")
            return

        script = Path(MAKIMA_SCRIPT)
        if not script.exists():
            self._log(f"ERROR: {MAKIMA_SCRIPT} not found.", "error")
            self._log("Place this launcher in the same folder as makima_assistant.py", "warn")
            return

        self._set_state(MakimaState.STARTING)
        self._log("Initializing Makima...", "warn")

        def launch():
            try:
                self.process = subprocess.Popen(
                    [PYTHON, MAKIMA_SCRIPT],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(script.parent)
                )
                self.uptime_start = time.time()
                self.after(0, lambda: self._set_state(MakimaState.ONLINE))
                self.after(0, lambda: self._log(f"Makima started  ·  PID {self.process.pid}", "success"))
                self.after(0, lambda: self._start_uptime_counter())

                # Stream stdout to log
                for line in self.process.stdout:
                    line = line.rstrip()
                    if line:
                        tag = "error" if "error" in line.lower() else \
                              "warn"  if "warn"  in line.lower() else \
                              "success" if any(w in line.lower() for w in ["ready","started","initialized","online"]) else \
                              "info"
                        self.after(0, lambda l=line, t=tag: self._log(l, t))

                self.process.wait()
                self.after(0, lambda: self._set_state(MakimaState.OFFLINE))
                self.after(0, lambda: self._log("Makima process exited.", "warn"))
                self.after(0, self._stop_uptime_counter)

            except Exception as ex:
                self.after(0, lambda: self._log(f"Launch error: {ex}", "error"))
                self.after(0, lambda: self._set_state(MakimaState.OFFLINE))

        threading.Thread(target=launch, daemon=True).start()

    def _stop_makima(self):
        if self.state_var == MakimaState.OFFLINE:
            self._log("Makima is not running.", "warn")
            return
        if not self.process:
            self._set_state(MakimaState.OFFLINE)
            return

        self._set_state(MakimaState.STOPPING)
        self._log("Sending stop signal...", "warn")

        def kill():
            try:
                # Try graceful first
                self.process.terminate()
                try:
                    self.process.wait(timeout=4)
                    self.after(0, lambda: self._log("Makima stopped gracefully.", "success"))
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.after(0, lambda: self._log("Makima force-killed.", "warn"))
            except Exception as ex:
                self.after(0, lambda: self._log(f"Stop error: {ex}", "error"))
            finally:
                self.process = None
                self.uptime_start = None
                self.after(0, lambda: self._set_state(MakimaState.OFFLINE))
                self.after(0, self._stop_uptime_counter)

        threading.Thread(target=kill, daemon=True).start()

    def _restart_makima(self):
        if self.state_var == MakimaState.OFFLINE:
            self._start_makima()
            return
        self._log("Restarting Makima...", "warn")

        def do_restart():
            self.after(0, self._stop_makima)
            time.sleep(2.5)
            self.after(0, self._start_makima)

        threading.Thread(target=do_restart, daemon=True).start()

    def _check_already_running(self):
        """Detect if makima_assistant.py is already running as a process."""
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if MAKIMA_SCRIPT in cmdline and proc.pid != os.getpid():
                    self._set_state(MakimaState.ONLINE)
                    self.uptime_start = time.time()
                    self._log(f"Detected running Makima  ·  PID {proc.pid}", "success")
                    self._start_uptime_counter()
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self._log("Makima is offline. Press START to launch.", "dim")

    # ── STATE MANAGEMENT ─────────────────────────────────────────────────────

    def _set_state(self, state):
        self.state_var = state

        labels = {
            MakimaState.OFFLINE:  ("OFFLINE",  C["crimson"], C["crimson_dim"]),
            MakimaState.STARTING: ("STARTING", "#f0c040",    "#1a1400"),
            MakimaState.ONLINE:   ("ONLINE",   C["green"],   C["green_dim"]),
            MakimaState.STOPPING: ("STOPPING", C["violet"],  C["violet_dim"]),
        }
        text, fg, bg = labels[state]

        self.status_pill.config(text=f"  ●  {text}  ", fg=fg, bg=bg)
        self.state_lbl.config(text=text, fg=fg)
        self._draw_orb(state)

        # Button states
        if state == MakimaState.ONLINE:
            self.start_btn.config(bg=C["surface"], fg=C["muted"])
            self.stop_btn.config(bg=C["crimson"],  fg=C["void"])
            self.restart_btn.config(bg=C["surface"], fg=C["muted"])
        elif state == MakimaState.OFFLINE:
            self.start_btn.config(bg=C["crimson"], fg=C["void"])
            self.stop_btn.config(bg=C["surface"],  fg=C["muted"])
            self.restart_btn.config(bg=C["surface"], fg=C["muted"])
        else:
            self.start_btn.config(bg=C["surface"],  fg=C["muted"])
            self.stop_btn.config(bg=C["surface"],   fg=C["muted"])
            self.restart_btn.config(bg=C["surface"], fg=C["muted"])

        self._refresh_status()

    def _refresh_status(self):
        """Update CPU/RAM/PID stats."""
        try:
            cpu = f"{psutil.cpu_percent(interval=None):.0f}"
            ram = f"{psutil.virtual_memory().percent:.0f}"
            self.stat_widgets["cpu"].config(text=cpu)
            self.stat_widgets["ram"].config(text=ram)

            if self.process and self.state_var == MakimaState.ONLINE:
                self.stat_widgets["pid"].config(text=str(self.process.pid), fg=C["green"])
            else:
                self.stat_widgets["pid"].config(text="—", fg=C["faint"])
        except Exception:
            pass

        self.after(2000, self._refresh_status)

    # ── UPTIME COUNTER ────────────────────────────────────────────────────────

    def _start_uptime_counter(self):
        self._tick_uptime()

    def _tick_uptime(self):
        if self.uptime_start and self.state_var == MakimaState.ONLINE:
            elapsed = int(time.time() - self.uptime_start)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.uptime_lbl.config(text=f"{h:02d}:{m:02d}:{s:02d}", fg=C["green"])
            self.stat_widgets["uptime"].config(
                text=f"{h:02d}:{m:02d}:{s:02d}", fg=C["green"])
            self._uptime_job = self.after(1000, self._tick_uptime)
        else:
            self.uptime_lbl.config(text="")
            self.stat_widgets["uptime"].config(text="—", fg=C["faint"])

    def _stop_uptime_counter(self):
        if self._uptime_job:
            self.after_cancel(self._uptime_job)
            self._uptime_job = None
        self.uptime_lbl.config(text="")
        self.stat_widgets["uptime"].config(text="—", fg=C["faint"])

    # ── LOG ───────────────────────────────────────────────────────────────────

    def _log(self, message, tag="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"[{timestamp}] ", "time")
        self.log_box.insert("end", message + "\n", tag)
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")
        self._log("Log cleared.", "dim")

    # ── CLOCK ─────────────────────────────────────────────────────────────────

    def _start_clock(self):
        def tick():
            self.clock_lbl.config(
                text=datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
            self.after(1000, tick)
        tick()

    # ── DRAG ─────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.winfo_x()
        self._drag_y = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ── CLOSE ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        if self.state_var == MakimaState.ONLINE:
            # Ask before closing if Makima is running
            confirm = tk.Toplevel(self)
            confirm.configure(bg=C["surface"])
            confirm.overrideredirect(True)
            confirm.resizable(False, False)
            w, h = 320, 140
            x = self.winfo_x() + (820 - w) // 2
            y = self.winfo_y() + (580 - h) // 2
            confirm.geometry(f"{w}x{h}+{x}+{y}")

            tk.Label(confirm, text="Stop Makima before closing?",
                     font=self.f_label, bg=C["surface"], fg=C["text"],
                     pady=20).pack()

            btn_row = tk.Frame(confirm, bg=C["surface"])
            btn_row.pack()

            def stop_and_close():
                confirm.destroy()
                self._stop_makima()
                self.after(2000, self.destroy)

            def just_close():
                confirm.destroy()
                self.destroy()

            tk.Label(btn_row, text="  STOP & CLOSE  ",
                     font=self.f_btn, bg=C["crimson"], fg=C["void"],
                     cursor="hand2", padx=8, pady=8).pack(side="left", padx=8)
            tk.Label(btn_row, text="  JUST CLOSE  ",
                     font=self.f_btn, bg=C["lift"], fg=C["muted"],
                     cursor="hand2", padx=8, pady=8).pack(side="left", padx=8)

            btn_row.winfo_children()[0].bind("<Button-1>", lambda e: stop_and_close())
            btn_row.winfo_children()[1].bind("<Button-1>", lambda e: just_close())
        else:
            self.destroy()


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = MakimaLauncher()
    app.mainloop()
