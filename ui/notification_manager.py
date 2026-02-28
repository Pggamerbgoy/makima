"""
ui/notification_manager.py

Desktop Notification Manager
──────────────────────────────
Cross-platform desktop notifications using win10toast (Windows)
or plyer (fallback). Includes a toggle for muting.
"""

import logging
import threading

logger = logging.getLogger("Makima.Notifications")

# Try win10toast first (Windows native), fallback to plyer
_BACKEND = None
try:
    from win10toast import ToastNotifier
    _BACKEND = "win10toast"
except ImportError:
    try:
        from plyer import notification as plyer_notification
        _BACKEND = "plyer"
    except ImportError:
        pass


class NotificationManager:
    """Send desktop notifications with a mute toggle."""

    def __init__(self):
        self.enabled: bool = True
        self._toaster = None
        if _BACKEND == "win10toast":
            try:
                self._toaster = ToastNotifier()
            except Exception:
                pass

    def toggle(self):
        self.enabled = not self.enabled

    def show_notification(self, title: str, message: str,
                          duration: int = 5, threaded: bool = True):
        """Show a desktop notification (non-blocking by default)."""
        if not self.enabled:
            return

        def _show():
            try:
                if _BACKEND == "win10toast" and self._toaster:
                    self._toaster.show_toast(
                        title, message, duration=duration, threaded=False
                    )
                elif _BACKEND == "plyer":
                    plyer_notification.notify(
                        title=title,
                        message=message,
                        timeout=duration,
                        app_name="Makima",
                    )
                else:
                    # No backend — just log
                    logger.debug(f"Notification (no backend): {title}: {message}")
            except Exception as e:
                logger.debug(f"Notification failed: {e}")

        if threaded:
            threading.Thread(target=_show, daemon=True).start()
        else:
            _show()
