"""
ui/voice_visualizer.py

Voice Waveform Visualizer
──────────────────────────
Animated circular / bar waveform shown while Makima is listening.
Uses QPainter for buttery-smooth 30 FPS rendering.
"""

import random
import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer, Qt, QRect
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QPen


class VoiceVisualizer(QWidget):
    """Floating waveform animation displayed during voice input."""

    BAR_COUNT = 24
    FPS = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 80)

        # Position above parent's voice button
        if parent:
            geo = parent.geometry()
            self.move(
                geo.x() + geo.width() // 2 - 150,
                geo.y() + geo.height() - 160,
            )

        # Bar heights (normalised 0‥1)
        self._bars = [0.1] * self.BAR_COUNT
        self._target_bars = [0.1] * self.BAR_COUNT
        self._active = True

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000 // self.FPS)

    # ── Animation loop ────────────────────────────────────────────────────────

    def _tick(self):
        if self._active:
            # Generate random target heights to simulate a live waveform
            for i in range(self.BAR_COUNT):
                self._target_bars[i] = random.uniform(0.15, 1.0)

        # Smooth interpolation toward target
        for i in range(self.BAR_COUNT):
            diff = self._target_bars[i] - self._bars[i]
            self._bars[i] += diff * 0.25

        self.update()

    def stop(self):
        """Collapse bars to zero and stop."""
        self._active = False
        self._target_bars = [0.05] * self.BAR_COUNT

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # Background pill
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(10, 14, 23, 220))
        painter.drawRoundedRect(0, 0, w, h, 16, 16)

        # Draw bars
        bar_width = max(4, (w - 40) // self.BAR_COUNT - 2)
        spacing = 2
        total_width = self.BAR_COUNT * (bar_width + spacing) - spacing
        x_start = (w - total_width) // 2

        for i, level in enumerate(self._bars):
            x = x_start + i * (bar_width + spacing)
            bar_h = int(level * (h - 20))
            y = (h - bar_h) // 2

            # Gradient per bar
            grad = QLinearGradient(x, y, x, y + bar_h)
            # Color shifts across the bar array for a rainbow-ish look
            hue = 180 + i * (60 / self.BAR_COUNT)  # cyan → blue-ish
            grad.setColorAt(0.0, QColor.fromHslF(hue / 360, 0.9, 0.65, 0.95))
            grad.setColorAt(1.0, QColor.fromHslF(hue / 360, 0.8, 0.45, 0.7))

            painter.setBrush(grad)
            painter.drawRoundedRect(x, y, bar_width, bar_h, 3, 3)

        # "Listening…" label
        painter.setPen(QColor(150, 160, 190))
        from PyQt5.QtGui import QFont
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRect(0, h - 18, w, 16), Qt.AlignCenter, "🎤 Listening…")

        painter.end()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
