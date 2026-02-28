"""
systems/notification_manager.py

Smart Notification Manager
────────────────────────────
Groups all system notifications and reads them on demand:
  - Captures Windows/Linux toast notifications
  - Groups by app (Discord, Slack, Teams, Email, etc.)
  - Reads them aloud on demand: "What notifications do I have?"
  - Priority filtering: only alerts for urgent notifications
  - Do Not Disturb mode: queues everything silently
  - Smart summarization: "5 Discord messages from John"

Commands:
  "What notifications do I have?"
  "Read my notifications"
  "Clear notifications"
  "Do not disturb mode"
  "Disable do not disturb"
  "Notification summary"
  "Any urgent notifications?"
"""

import os
import time
import json
import logging
import threading
import platform
from datetime import datetime
from collections import defaultdict
from typing import Callable, Optional

logger = logging.getLogger("Makima.Notifications")
OS = platform.system()

NOTIF_LOG_FILE = "notifications.json"

PRIORITY_APPS = {"slack", "teams", "zoom", "outlook", "gmail", "phone"}
GROUP_BY_APP = True
MAX_STORED = 50


class NotificationEntry:
    def __init__(self, app: str, title: str, body: str):
        self.app = app
        self.title = title
        self.body = body
        self.time = datetime.now()
        self.read = False

    def to_dict(self) -> dict:
        return {
            "app": self.app, "title": self.title, "body": self.body,
            "time": self.time.strftime("%H:%M"), "read": self.read,
        }


class NotificationManager:

    def __init__(self, ai, speak_callback: Callable):
        self.ai = ai
        self.speak = speak_callback
        self.dnd = False
        self._notifications: list[NotificationEntry] = []
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    # ── Capture ───────────────────────────────────────────────────────────────

    def _capture_loop(self):
        if OS == "Windows":
            self._capture_windows()
        elif OS == "Linux":
            self._capture_linux()

    def _capture_windows(self):
        """Capture Windows toast notifications via WinRT."""
        try:
            from winrt.windows.ui.notifications.management import (
                UserNotificationListener,
                UserNotificationListenerAccessStatus,
            )
            from winrt.windows.ui.notifications import KnownNotificationBindings

            listener = UserNotificationListener.current
            access = await_or_run(listener.request_access_async())

            def on_notif_changed(sender, args):
                try:
                    notifs = await_or_run(sender.get_notifications_async(
                        UserNotificationListenerAccessStatus.allowed
                    ))
                    for n in notifs:
                        binding = n.notification.visual.get_binding(
                            KnownNotificationBindings.toast_generic()
                        )
                        if binding:
                            texts = binding.get_text_elements()
                            title = texts[0].text if texts else ""
                            body = texts[1].text if len(texts) > 1 else ""
                            app = n.app_info.display_info.display_name if n.app_info else "Unknown"
                            self._add(app, title, body)
                except Exception:
                    pass

            listener.notification_changed += on_notif_changed
            while self._running:
                time.sleep(5)
        except Exception as e:
            logger.debug(f"Windows notification capture: {e}")
            self._capture_polling_fallback()

    def _capture_linux(self):
        """Capture Linux notifications via DBus."""
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            from gi.repository import GLib

            DBusGMainLoop(set_as_default=True)
            bus = dbus.SessionBus()

            def notif_handler(bus_name, path, iface, member, args):
                if member == "Notify":
                    app = str(args[0]) if args else "Unknown"
                    title = str(args[3]) if len(args) > 3 else ""
                    body = str(args[4]) if len(args) > 4 else ""
                    self._add(app, title, body)

            bus.add_match_string("type='method_call',interface='org.freedesktop.Notifications'")
            bus.add_message_filter(notif_handler)
            loop = GLib.MainLoop()
            loop.run()
        except Exception as e:
            logger.debug(f"Linux notification capture: {e}")
            self._capture_polling_fallback()

    def _capture_polling_fallback(self):
        """Fallback: simulate capturing by watching for known app processes."""
        while self._running:
            time.sleep(30)

    def add_manual(self, app: str, title: str, body: str = ""):
        """Manually inject a notification (for testing or integrations)."""
        self._add(app, title, body)

    def _add(self, app: str, title: str, body: str):
        entry = NotificationEntry(app, title, body)
        with self._lock:
            self._notifications.append(entry)
            if len(self._notifications) > MAX_STORED:
                self._notifications = self._notifications[-MAX_STORED:]

        # Alert for priority apps if not in DND
        if not self.dnd and app.lower() in PRIORITY_APPS:
            self.speak(f"Priority notification from {app}: {title}")

        logger.debug(f"[{app}] {title}: {body[:50]}")

    # ── Reading ───────────────────────────────────────────────────────────────

    def get_summary(self) -> str:
        with self._lock:
            unread = [n for n in self._notifications if not n.read]

        if not unread:
            return "No unread notifications."

        # Group by app
        groups: dict[str, list] = defaultdict(list)
        for n in unread:
            groups[n.app].append(n)

        lines = [f"📬 {len(unread)} notification{'s' if len(unread) != 1 else ''}:"]
        for app, notifs in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)[:6]:
            if len(notifs) == 1:
                n = notifs[0]
                lines.append(f"  [{n.time.strftime('%H:%M')}] {app}: {n.title}")
            else:
                # Summarize multiple
                titles = [n.title for n in notifs[-3:]]
                lines.append(f"  {app}: {len(notifs)} messages — latest: {titles[-1][:40]}")

        return "\n".join(lines)

    def get_urgent(self) -> str:
        with self._lock:
            urgent = [
                n for n in self._notifications
                if not n.read and n.app.lower() in PRIORITY_APPS
            ]
        if not urgent:
            return "No urgent notifications."
        lines = [f"⚠️ {len(urgent)} urgent notification(s):"]
        for n in urgent[:5]:
            lines.append(f"  [{n.time.strftime('%H:%M')}] {n.app}: {n.title}")
        return "\n".join(lines)

    def read_aloud(self) -> str:
        summary = self.get_summary()
        return summary

    def clear(self) -> str:
        with self._lock:
            count = sum(1 for n in self._notifications if not n.read)
            for n in self._notifications:
                n.read = True
        return f"Cleared {count} notifications."

    def enable_dnd(self) -> str:
        self.dnd = True
        return "Do Not Disturb enabled. I'll hold all notifications until you ask."

    def disable_dnd(self) -> str:
        self.dnd = False
        with self._lock:
            pending = sum(1 for n in self._notifications if not n.read)
        msg = f"Do Not Disturb off."
        if pending:
            msg += f" You have {pending} pending notifications."
        return msg

    def get_status(self) -> str:
        with self._lock:
            unread = sum(1 for n in self._notifications if not n.read)
        dnd_str = " (DND on)" if self.dnd else ""
        return f"Notifications: {unread} unread{dnd_str}."
