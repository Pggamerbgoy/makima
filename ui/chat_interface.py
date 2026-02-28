"""
ui/chat_interface.py

🌸 Makima Enhanced Chat Interface
────────────────────────────────────
Premium PyQt5 desktop UI with:
  • Animated chat bubbles with fade-in
  • Fenced code block syntax highlighting
  • Integrated Music DJ panel (album art, mood buttons, playlist)
  • Drag-and-drop file attachments
  • Voice input with waveform visualizer
  • Theme switching (dark_cyber, light, nord, dracula, matrix)
  • Mini-mode floating window
  • Desktop notifications
  • Chat history with search
  • Settings dialog
"""

import sys
import os
import threading
import logging
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QTextEdit, QScrollArea, QGridLayout,
    QListWidget, QListWidgetItem, QSlider, QMenu, QFileDialog,
    QGraphicsOpacityEffect, QDialog, QLineEdit, QSizePolicy,
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal, QEvent, QSize,
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QPixmap, QCursor, QIcon,
)

# Local modules
from ui.settings_dialog import SettingsDialog
from ui.mini_mode import MiniModeWindow
from ui.theme_manager import ThemeManager, ThemeCreatorDialog
from ui.chat_history import ChatHistory
from ui.notification_manager import NotificationManager
from ui.code_highlighter import CodeHighlighter
from ui.voice_visualizer import VoiceVisualizer
from ui.file_handler import FileDropArea

logger = logging.getLogger("Makima.ChatUI")


# ═══════════════════════════════════════════════════════════════════════════════
# AnimatedButton
# ═══════════════════════════════════════════════════════════════════════════════

class AnimatedButton(QPushButton):
    """Button with a subtle hover scale animation."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(100)
        self._original: QSize | None = None

    def enterEvent(self, event):
        if self._original is None:
            self._original = self.size()
        target = QRect(self.geometry())
        target.setWidth(int(self.width() * 1.05))
        target.setHeight(int(self.height() * 1.05))
        self._anim.setEndValue(target)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._original:
            target = QRect(self.geometry())
            target.setSize(self._original)
            self._anim.setEndValue(target)
            self._anim.start()
        super().leaveEvent(event)


# ═══════════════════════════════════════════════════════════════════════════════
# ChatBubble
# ═══════════════════════════════════════════════════════════════════════════════

class ChatBubble(QWidget):
    """Individual chat message bubble with fade-in, code highlighting, and
    optional file-attachment chips."""

    def __init__(self, message: str, is_user: bool = True,
                 timestamp: str = None, has_code: bool = False,
                 files: list = None):
        super().__init__()
        self.message = message
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now().strftime("%I:%M %p")
        self.has_code = has_code or ("```" in message)
        self.files = files or []
        self._build()
        self._fade_in()

    def _fade_in(self):
        self._opacity = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self._opacity)
        anim = QPropertyAnimation(self._opacity, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()
        self._fade_anim = anim  # prevent GC

    def _build(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        bubble = QFrame()
        bubble.setObjectName("userBubble" if self.is_user else "makimaBubble")

        bl = QVBoxLayout()
        bl.setSpacing(5)

        # File chips
        if self.files:
            for fp in self.files:
                btn = QPushButton(f"📎 {os.path.basename(fp)}")
                btn.setObjectName("fileAttachment")
                btn.clicked.connect(lambda _, p=fp: os.startfile(p))
                bl.addWidget(btn)

        # Message body
        if self.has_code:
            body = CodeHighlighter.create_highlighted_widget(self.message)
        else:
            body = QLabel(self.message)
            body.setWordWrap(True)
            body.setTextInteractionFlags(
                Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
            )
            body.setOpenExternalLinks(True)
            body.setObjectName("messageText")
        bl.addWidget(body)

        # Timestamp
        ts = QLabel(self.timestamp)
        ts.setObjectName("timestamp")
        ts.setAlignment(Qt.AlignRight if self.is_user else Qt.AlignLeft)
        bl.addWidget(ts)

        bubble.setLayout(bl)

        if self.is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()

        self.setLayout(layout)


# ═══════════════════════════════════════════════════════════════════════════════
# MusicControlWidget
# ═══════════════════════════════════════════════════════════════════════════════

class MusicControlWidget(QWidget):
    """Right-side panel: album art, playback controls, mood buttons, playlist."""

    def __init__(self, music_dj):
        super().__init__()
        self.dj = music_dj
        self._build()
        self._start_poller()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Album art
        self.album_art = QLabel()
        self.album_art.setObjectName("albumArt")
        self.album_art.setFixedSize(200, 200)
        self.album_art.setAlignment(Qt.AlignCenter)
        self.album_art.setScaledContents(True)
        self._set_default_art()
        layout.addWidget(self.album_art, alignment=Qt.AlignCenter)

        # Now-playing frame
        np = QFrame()
        np.setObjectName("nowPlayingFrame")
        npl = QVBoxLayout()
        self.track_label = QLabel("No music playing")
        self.track_label.setObjectName("trackLabel")
        self.track_label.setWordWrap(True)
        self.track_label.setAlignment(Qt.AlignCenter)
        npl.addWidget(self.track_label)
        self.artist_label = QLabel("")
        self.artist_label.setObjectName("artistLabel")
        self.artist_label.setAlignment(Qt.AlignCenter)
        npl.addWidget(self.artist_label)
        np.setLayout(npl)
        layout.addWidget(np)

        # Progress
        self.progress = QSlider(Qt.Horizontal)
        self.progress.setObjectName("progressBar")
        self.progress.setEnabled(False)
        layout.addWidget(self.progress)

        time_row = QHBoxLayout()
        self.time_cur = QLabel("0:00")
        self.time_cur.setObjectName("timeLabel")
        self.time_tot = QLabel("0:00")
        self.time_tot.setObjectName("timeLabel")
        time_row.addWidget(self.time_cur)
        time_row.addStretch()
        time_row.addWidget(self.time_tot)
        layout.addLayout(time_row)

        # Playback controls
        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)

        self.prev_btn = AnimatedButton("⏮")
        self.prev_btn.setObjectName("controlButton")
        self.prev_btn.clicked.connect(self._prev)

        self.play_btn = AnimatedButton("▶")
        self.play_btn.setObjectName("playButton")
        self.play_btn.clicked.connect(self._toggle_play)

        self.next_btn = AnimatedButton("⏭")
        self.next_btn.setObjectName("controlButton")
        self.next_btn.clicked.connect(self._next)

        self.shuf_btn = AnimatedButton("🔀")
        self.shuf_btn.setObjectName("controlButton")
        self.shuf_btn.clicked.connect(self._shuffle)

        self.repeat_btn = AnimatedButton("🔁")
        self.repeat_btn.setObjectName("controlButton")
        self.repeat_btn.clicked.connect(self._repeat)

        for b in (self.prev_btn, self.play_btn, self.next_btn,
                  self.shuf_btn, self.repeat_btn):
            ctrl.addWidget(b)
        layout.addLayout(ctrl)

        # Volume
        vol = QHBoxLayout()
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setObjectName("muteButton")
        self.mute_btn.clicked.connect(self._mute_toggle)
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(50)
        self.vol_slider.setObjectName("volumeSlider")
        self.vol_slider.valueChanged.connect(self._vol_changed)
        self.vol_label = QLabel("50%")
        self.vol_label.setObjectName("volumeLabel")
        vol.addWidget(self.mute_btn)
        vol.addWidget(self.vol_slider)
        vol.addWidget(self.vol_label)
        layout.addLayout(vol)

        # Mood quick-buttons
        section = QLabel("🎭 Quick Moods")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        mood_grid = QGridLayout()
        mood_grid.setSpacing(8)
        moods = [
            ("🎯 Focus",  "focus"),  ("🔥 Hype",   "hype"),
            ("😌 Chill",  "chill"),  ("😢 Sad",    "sad"),
            ("🎮 Gaming", "gaming"), ("💻 Coding", "coding"),
            ("🎉 Party",  "party"),  ("😴 Sleep",  "sleep"),
        ]
        for i, (label, mood) in enumerate(moods):
            btn = AnimatedButton(label)
            btn.setObjectName("moodButton")
            btn.clicked.connect(lambda _, m=mood: self._play_mood(m))
            mood_grid.addWidget(btn, i // 2, i % 2)
        layout.addLayout(mood_grid)

        # Playlist
        pl = QLabel("📋 Up Next")
        pl.setObjectName("sectionTitle")
        layout.addWidget(pl)
        self.playlist = QListWidget()
        self.playlist.setObjectName("playlistWidget")
        self.playlist.setMaximumHeight(150)
        layout.addWidget(self.playlist)

        layout.addStretch()
        self.setLayout(layout)

    # ── Poller ────────────────────────────────────────────────────────────────

    def _start_poller(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(2500)

    def _poll(self):
        """Update now-playing info from Spotify."""
        try:
            if not self.dj or not self.dj.sp:
                return
            cur = self.dj.sp.current_playback()
            if cur and cur.get("is_playing") and cur.get("item"):
                item = cur["item"]
                self.track_label.setText(item["name"])
                self.artist_label.setText(
                    ", ".join(a["name"] for a in item["artists"])
                )
                self.play_btn.setText("⏸")
                dur = item["duration_ms"] / 1000
                prog = cur["progress_ms"] / 1000
                self.progress.setMaximum(int(dur))
                self.progress.setValue(int(prog))
                self.time_cur.setText(self._fmt(prog))
                self.time_tot.setText(self._fmt(dur))
                self._update_art(item)
            else:
                self.track_label.setText("No music playing")
                self.artist_label.setText("")
                self.play_btn.setText("▶")
                self._set_default_art()
        except Exception:
            pass

    @staticmethod
    def _fmt(secs: float) -> str:
        m, s = divmod(int(secs), 60)
        return f"{m}:{s:02d}"

    # ── Art ───────────────────────────────────────────────────────────────────

    def _set_default_art(self):
        px = QPixmap(200, 200)
        px.fill(QColor("#1a1a2e"))
        p = QPainter(px)
        p.setPen(QColor("#00d9ff"))
        p.setFont(QFont("Arial", 48))
        p.drawText(px.rect(), Qt.AlignCenter, "🎵")
        p.end()
        self.album_art.setPixmap(px)

    def _update_art(self, item):
        """Show first letter of track name as placeholder art."""
        try:
            ch = item["name"][0].upper()
            px = QPixmap(200, 200)
            px.fill(QColor("#1a1a2e"))
            p = QPainter(px)
            p.setPen(QColor("#00d9ff"))
            p.setFont(QFont("Arial", 72, QFont.Bold))
            p.drawText(px.rect(), Qt.AlignCenter, ch)
            p.end()
            self.album_art.setPixmap(px)
        except Exception:
            self._set_default_art()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _toggle_play(self):
        if not self.dj:
            return
        try:
            cur = self.dj.sp.current_playback()
            if cur and cur.get("is_playing"):
                self.dj.pause()
                self.play_btn.setText("▶")
            else:
                self.dj.resume()
                self.play_btn.setText("⏸")
        except Exception:
            pass

    def _prev(self):
        if self.dj:
            self.dj.previous()
            QTimer.singleShot(600, self._poll)

    def _next(self):
        if self.dj:
            self.dj.skip()
            QTimer.singleShot(600, self._poll)

    def _shuffle(self):
        if self.dj:
            res = self.dj.toggle_shuffle()
            active = "ON" in res if res else False
            self.shuf_btn.setStyleSheet(
                "background-color: #00d9ff;" if active else ""
            )

    def _repeat(self):
        if not self.dj or not self.dj.sp:
            return
        try:
            cur = self.dj.sp.current_playback()
            state = cur.get("repeat_state", "off")
            new = "context" if state == "off" else "off"
            self.dj.sp.repeat(new)
            self.repeat_btn.setStyleSheet(
                "background-color: #00d9ff;" if new != "off" else ""
            )
        except Exception:
            pass

    def _mute_toggle(self):
        v = self.vol_slider.value()
        if v > 0:
            self._prev_vol = v
            self.vol_slider.setValue(0)
            self.mute_btn.setText("🔇")
        else:
            self.vol_slider.setValue(getattr(self, "_prev_vol", 50))
            self.mute_btn.setText("🔊")

    def _vol_changed(self, val):
        try:
            if self.dj and self.dj.sp:
                self.dj.sp.volume(val)
        except Exception:
            pass
        self.vol_label.setText(f"{val}%")
        self.mute_btn.setText("🔇" if val == 0 else "🔊")

    def _play_mood(self, mood: str):
        if self.dj:
            threading.Thread(
                target=lambda: self.dj.play_mood(mood),
                daemon=True,
            ).start()
            QTimer.singleShot(1500, self._poll)


# ═══════════════════════════════════════════════════════════════════════════════
# ChatInterface (Main Window)
# ═══════════════════════════════════════════════════════════════════════════════

class ChatInterface(QMainWindow):
    """The primary Makima desktop UI."""

    # Thread-safe signals
    _sig_message  = pyqtSignal(str, bool, list)   # text, is_user, files
    _sig_status   = pyqtSignal(str, str)           # text, color

    def __init__(self, makima_instance):
        super().__init__()
        self.makima = makima_instance

        # Managers
        self.theme_mgr    = ThemeManager()
        self.chat_history = ChatHistory()
        self.notif_mgr    = NotificationManager()

        # Music DJ — grab from Makima or lazy-create
        self.music_dj = getattr(makima_instance.manager.music, "_dj", None)
        if self.music_dj is None:
            try:
                from systems.music_dj import MusicDJ
                self.music_dj = MusicDJ(speak_callback=makima_instance.speak)
            except Exception:
                self.music_dj = None

        # State
        self.mini_window   = None
        self.voice_viz     = None
        self.attached_files: list[str] = []

        self._build_ui()

        # Connect signals
        self._sig_message.connect(self._on_message)
        self._sig_status.connect(self._on_status)

        # Load recent history
        self._load_history()

        # Apply default theme
        self.apply_theme(self.theme_mgr.current_theme)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("🌸 Makima AI Assistant")
        self.setGeometry(100, 100, 1400, 900)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout()
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Left: chat area ──
        chat_box = QWidget()
        chat_box.setObjectName("chatContainer")
        cl = QVBoxLayout()
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        cl.addWidget(self._make_header())

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("chatScroll")

        # File drop overlay
        self.file_drop = FileDropArea(self.scroll)
        self.file_drop.files_dropped.connect(self._on_files_dropped)

        self.chat_widget = QWidget()
        self.chat_vbox = QVBoxLayout()
        self.chat_vbox.setAlignment(Qt.AlignTop)
        self.chat_vbox.setSpacing(10)
        self.chat_widget.setLayout(self.chat_vbox)
        self.scroll.setWidget(self.chat_widget)
        cl.addWidget(self.scroll)

        cl.addWidget(self._make_input_area())
        chat_box.setLayout(cl)
        root.addWidget(chat_box, 7)

        # ── Right: music panel ──
        music_box = QWidget()
        music_box.setObjectName("musicPanel")
        ml = QVBoxLayout()
        ml.setContentsMargins(0, 0, 0, 0)
        self.music_panel = MusicControlWidget(self.music_dj)
        ml.addWidget(self.music_panel)
        music_box.setLayout(ml)
        root.addWidget(music_box, 3)

        central.setLayout(root)

        # Welcome
        self._add_bubble(
            "👋 Hey! I'm Makima, your AI assistant.\n\n"
            "✨ Features:\n"
            "• Voice commands (click 🎤)\n"
            "• Music control (try 'play focus music')\n"
            "• File sharing (drag & drop files)\n"
            "• Code highlighting\n"
            "• Smart notifications\n\n"
            "How can I help you today?",
            is_user=False,
        )

    # ── Header ────────────────────────────────────────────────────────────────

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(80)
        hl = QHBoxLayout()
        hl.setContentsMargins(20, 0, 20, 0)

        avatar = QLabel("🎭")
        avatar.setObjectName("avatar")
        hl.addWidget(avatar)

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        n = QLabel("Makima")
        n.setObjectName("headerName")
        self.status_label = QLabel("🟢 Online")
        self.status_label.setObjectName("statusLabel")
        name_col.addWidget(n)
        name_col.addWidget(self.status_label)
        hl.addLayout(name_col)
        hl.addStretch()

        btns = [
            ("📜", "Chat History",  self._show_history),
            ("📖", "Learn This App", self._learn_current_app),
            ("🎨", "Change Theme",  self._show_theme_menu),
            ("🗗",  "Mini Mode",     self._toggle_mini),
            ("⚙",  "Settings",      self._open_settings),
        ]
        for icon, tip, slot in btns:
            b = QPushButton(icon)
            b.setObjectName("headerButton")
            b.setToolTip(tip)
            b.clicked.connect(slot)
            hl.addWidget(b)

        self.notif_btn = QPushButton("🔔")
        self.notif_btn.setObjectName("headerButton")
        self.notif_btn.setToolTip("Notifications: ON")
        self.notif_btn.clicked.connect(self._toggle_notifs)
        hl.addWidget(self.notif_btn)

        header.setLayout(hl)
        return header

    # ── Input Area ────────────────────────────────────────────────────────────

    def _make_input_area(self) -> QFrame:
        container = QFrame()
        container.setObjectName("inputContainer")
        outer = QVBoxLayout()
        outer.setContentsMargins(20, 15, 20, 15)

        # Attachment bar (hidden)
        self.attach_bar = QWidget()
        self.attach_bar_layout = QHBoxLayout()
        self.attach_bar.setLayout(self.attach_bar_layout)
        self.attach_bar.hide()
        outer.addWidget(self.attach_bar)

        row = QHBoxLayout()

        attach = QPushButton("📎")
        attach.setObjectName("attachButton")
        attach.setToolTip("Attach File")
        attach.setFixedSize(60, 70)
        attach.clicked.connect(self._attach_file)
        row.addWidget(attach)

        self.msg_input = QTextEdit()
        self.msg_input.setObjectName("messageInput")
        self.msg_input.setPlaceholderText(
            "Type your message… (Shift+Enter for new line)"
        )
        self.msg_input.setFixedHeight(70)
        self.msg_input.installEventFilter(self)
        row.addWidget(self.msg_input)

        self.send_btn = AnimatedButton("Send")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setFixedSize(90, 70)
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)

        self.voice_btn = AnimatedButton("🎤")
        self.voice_btn.setObjectName("voiceButton")
        self.voice_btn.setFixedSize(70, 70)
        self.voice_btn.clicked.connect(self._toggle_voice)
        row.addWidget(self.voice_btn)

        outer.addLayout(row)
        container.setLayout(outer)
        return container

    # ── Event Filter (Enter to send) ──────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self.msg_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self._send()
                return True
        return super().eventFilter(obj, event)

    # ── Send / Process ────────────────────────────────────────────────────────

    def _send(self):
        text = self.msg_input.toPlainText().strip()
        if not text and not self.attached_files:
            return
        self.msg_input.clear()
        files = self.attached_files.copy()
        self.attached_files.clear()
        self._refresh_attachments()

        self._add_bubble(text, is_user=True, files=files)
        self._sig_status.emit("🔄 Thinking…", "#FFA500")

        threading.Thread(
            target=self._process, args=(text, files), daemon=True
        ).start()

    def _process(self, text: str, files: list):
        try:
            response = self.makima.process_input(text)
            response = response or "Done."
        except Exception as e:
            response = f"⚠️ Error: {e}"

        self._sig_message.emit(response, False, [])
        self._sig_status.emit("🟢 Online", "#00ff88")

        if self.notif_mgr.enabled and len(response) > 5:
            preview = response[:100] + ("…" if len(response) > 100 else "")
            self.notif_mgr.show_notification("Makima", preview)

    # ── Bubble management ─────────────────────────────────────────────────────

    def _add_bubble(self, text: str, is_user: bool = True, files: list = None):
        """Thread-safe: can be called from any thread via signal."""
        self._sig_message.emit(text, is_user, files or [])

    def _on_message(self, text: str, is_user: bool, files: list):
        bubble = ChatBubble(text, is_user, files=files)
        self.chat_vbox.addWidget(bubble)
        self.chat_history.add_message(text, is_user, files)
        QTimer.singleShot(80, self._scroll_bottom)

    def _scroll_bottom(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_status(self, text: str, color: str):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    # ── Attachments ───────────────────────────────────────────────────────────

    def _attach_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All (*.*)")
        if paths:
            self._on_files_dropped(paths)

    def _on_files_dropped(self, paths: list):
        self.attached_files.extend(paths)
        self._refresh_attachments()

    def _refresh_attachments(self):
        while self.attach_bar_layout.count():
            w = self.attach_bar_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        if self.attached_files:
            self.attach_bar.show()
            for fp in self.attached_files:
                chip = QFrame()
                chip.setObjectName("attachmentChip")
                cl = QHBoxLayout()
                cl.setContentsMargins(8, 2, 8, 2)
                lbl = QLabel(f"📎 {os.path.basename(fp)}")
                lbl.setObjectName("attachmentLabel")
                rm = QPushButton("✕")
                rm.setObjectName("removeAttachmentButton")
                rm.setFixedSize(20, 20)
                rm.clicked.connect(lambda _, p=fp: self._remove_attach(p))
                cl.addWidget(lbl)
                cl.addWidget(rm)
                chip.setLayout(cl)
                self.attach_bar_layout.addWidget(chip)
            self.attach_bar_layout.addStretch()
        else:
            self.attach_bar.hide()

    def _remove_attach(self, path: str):
        if path in self.attached_files:
            self.attached_files.remove(path)
            self._refresh_attachments()

    # ── Voice ─────────────────────────────────────────────────────────────────

    def _toggle_voice(self):
        if self.voice_btn.text() == "🎤":
            self.voice_btn.setText("⏹")
            self.voice_btn.setObjectName("voiceButtonActive")
            self.voice_btn.setStyle(self.voice_btn.style())
            self.voice_viz = VoiceVisualizer(self)
            self.voice_viz.show()
            threading.Thread(target=self._listen, daemon=True).start()
        else:
            self._stop_voice()

    def _listen(self):
        try:
            cmd = self.makima.listen_once()
            if cmd:
                self.msg_input.setText(cmd)
                self._send()
        except Exception as e:
            logger.warning(f"Voice error: {e}")
        finally:
            self._stop_voice()

    def _stop_voice(self):
        self.voice_btn.setText("🎤")
        self.voice_btn.setObjectName("voiceButton")
        self.voice_btn.setStyle(self.voice_btn.style())
        if self.voice_viz:
            self.voice_viz.close()
            self.voice_viz = None

    # ── History ───────────────────────────────────────────────────────────────

    def _show_history(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("📜 Chat History")
        dlg.setFixedSize(600, 700)

        lo = QVBoxLayout()

        search_row = QHBoxLayout()
        search_in = QLineEdit()
        search_in.setPlaceholderText("Search messages…")
        search_btn = QPushButton("🔍")
        search_row.addWidget(search_in)
        search_row.addWidget(search_btn)
        lo.addLayout(search_row)

        hlist = QListWidget()
        for s in self.chat_history.get_sessions():
            hlist.addItem(f"{s['date']}  —  {s['message_count']} messages")
        lo.addWidget(hlist)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.close)
        lo.addWidget(close_btn, alignment=Qt.AlignRight)

        dlg.setLayout(lo)
        dlg.exec_()

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _show_theme_menu(self):
        """Show theme selector with grid previews."""
        self._show_theme_selector()

    def _show_theme_selector(self):
        """Full theme selector dialog with preview cards."""
        dialog = QDialog(self)
        dialog.setWindowTitle("🎨 Choose Your Theme")
        dialog.setFixedSize(820, 620)

        layout = QVBoxLayout()

        title = QLabel("🎨 Select Your Theme")
        title.setStyleSheet(
            "font-size: 20px; font-weight: bold; padding: 10px;"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Scrollable grid of theme previews
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout()
        grid.setSpacing(16)

        themes = self.theme_mgr.get_available_themes()
        for i, theme_name in enumerate(themes):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { border: 1px solid #333; border-radius: 10px;"
                "  padding: 8px; }"
            )
            cl = QVBoxLayout()
            cl.setSpacing(8)

            preview = self.theme_mgr.create_theme_preview(theme_name)
            cl.addWidget(preview, alignment=Qt.AlignCenter)

            apply_btn = QPushButton(
                f"Apply {theme_name.replace('_', ' ').title()}"
            )
            apply_btn.clicked.connect(
                lambda _, t=theme_name, d=dialog: self._apply_and_close(t, d)
            )
            cl.addWidget(apply_btn)

            card.setLayout(cl)
            grid.addWidget(card, i // 3, i % 3)

        inner.setLayout(grid)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        # Custom theme creator button
        custom_btn = QPushButton("➕ Create Custom Theme")
        custom_btn.clicked.connect(lambda: self._open_theme_creator(dialog))
        layout.addWidget(custom_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def _apply_and_close(self, theme_name: str, dialog: QDialog):
        """Apply selected theme and close the selector."""
        self.apply_theme(theme_name)
        dialog.accept()

    def _open_theme_creator(self, parent_dialog: QDialog = None):
        """Open the custom theme creator."""
        creator = ThemeCreatorDialog(self.theme_mgr, self)
        creator.exec_()

    def apply_theme(self, name: str):
        qss = self.theme_mgr.load_theme(name)
        self.setStyleSheet(qss)

    # ── Mini mode ─────────────────────────────────────────────────────────────

    def _toggle_mini(self):
        self.mini_window = MiniModeWindow(self.makima)
        self.mini_window.expand_requested.connect(self._expand_from_mini)
        self.mini_window.show()
        self.hide()

    def _expand_from_mini(self):
        self.show()

    # ── Notifications ─────────────────────────────────────────────────────────

    def _toggle_notifs(self):
        self.notif_mgr.toggle()
        if self.notif_mgr.enabled:
            self.notif_btn.setText("🔔")
            self.notif_btn.setToolTip("Notifications: ON")
        else:
            self.notif_btn.setText("🔕")
            self.notif_btn.setToolTip("Notifications: OFF")

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsDialog(self.makima, self).exec_()

    # ── Learn App ─────────────────────────────────────────────────────────────

    def _learn_current_app(self):
        """Ask AppLearner to learn whatever app is currently active."""
        learner = getattr(self.makima, 'app_learner', None)
        if not learner:
            self._sig_message.emit(
                "⚠️ App Learner is not available.", False, []
            )
            return
        self._sig_message.emit(
            "📖 Learning the currently active app...", False, []
        )
        import threading
        def _do():
            result = learner.learn_current_app()
            self._sig_message.emit(result or "Done.", False, [])
        threading.Thread(target=_do, daemon=True).start()

    # ── History warm-up ───────────────────────────────────────────────────────

    def _load_history(self):
        for msg in self.chat_history.get_recent_messages(10):
            if msg.get("message"):
                bubble = ChatBubble(
                    msg["message"],
                    msg["is_user"],
                    msg.get("timestamp"),
                    files=msg.get("files", []),
                )
                self.chat_vbox.addWidget(bubble)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self.chat_history.save()
        event.accept()


# ═══════════════════════════════════════════════════════════════════════════════
# Launcher
# ═══════════════════════════════════════════════════════════════════════════════

def launch_ui(makima_instance):
    """Create QApplication and show the ChatInterface window."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ChatInterface(makima_instance)
    window.show()
    sys.exit(app.exec_())
