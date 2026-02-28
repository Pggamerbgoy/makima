"""
ui/file_handler.py

File Drag-and-Drop Handler
────────────────────────────
A transparent overlay widget that accepts drag-and-drop files
and emits a signal with the list of dropped file paths.
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QColor, QPainter, QPen, QFont


class FileDropArea(QWidget):
    """Invisible overlay that becomes visible on drag-enter, accepts file drops."""

    files_dropped = pyqtSignal(list)  # emits list[str] of absolute paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._dragging = False
        self.hide()  # invisible until a drag enters the parent

    # ── Drag events ───────────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._dragging = True
            # Show ourselves as an overlay
            self.setGeometry(self.parent().rect())
            self.show()
            self.raise_()
            self.update()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._dragging = False
        self.hide()

    def dropEvent(self, event):
        self._dragging = False
        self.hide()

        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                local = url.toLocalFile()
                if local:
                    paths.append(local)
            if paths:
                self.files_dropped.emit(paths)
        event.acceptProposedAction()

    # ── Visual feedback ───────────────────────────────────────────────────────

    def paintEvent(self, event):
        if not self._dragging:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Semi-transparent overlay
        painter.fillRect(self.rect(), QColor(0, 217, 255, 30))

        # Dashed border
        pen = QPen(QColor(0, 217, 255, 180), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.drawRoundedRect(
            8, 8, self.width() - 16, self.height() - 16, 12, 12
        )

        # Centered label
        painter.setPen(QColor(0, 217, 255, 220))
        painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, "📎  Drop files here")

        painter.end()
