"""
systems/reminder.py
Time-based reminder system that fires spoken alerts.
"""

import re
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable

logger = logging.getLogger("Makima.Reminders")


def _parse_time_str(time_str: str) -> Optional[datetime]:
    """Parse time strings like '3pm', '15:30', 'in 5 minutes'."""
    time_str = time_str.lower().strip()
    now = datetime.now()

    # "in X minutes/hours"
    m = re.match(r"in (\d+) (minute|hour)s?", time_str)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(minutes=amount) if unit == "minute" else timedelta(hours=amount)
        return now + delta

    # "at HH:MM" or "at H:MM am/pm"
    m = re.match(r"(?:at )?(\d{1,2}):(\d{2})\s*(am|pm)?", time_str)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        meridiem = m.group(3)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # "at Xpm" / "at Xam"
    m = re.match(r"(?:at )?(\d{1,2})\s*(am|pm)", time_str)
    if m:
        hour = int(m.group(1))
        meridiem = m.group(2)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    return None


class ReminderSystem:

    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback  # will be set to makima.speak later
        self._reminders: list[dict] = []
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def set_callback(self, callback: Callable[[str], None]):
        self.callback = callback

    def add(self, task: str, time_str: str) -> str:
        target = _parse_time_str(time_str)
        if not target:
            return f"I couldn't understand the time '{time_str}'. Try '3pm', '15:30', or 'in 10 minutes'."
        with self._lock:
            self._reminders.append({"task": task, "time": target, "fired": False})
        return f"Got it! I'll remind you to {task} at {target.strftime('%I:%M %p')}."

    def _loop(self):
        while True:
            now = datetime.now()
            with self._lock:
                for reminder in self._reminders:
                    if not reminder["fired"] and now >= reminder["time"]:
                        reminder["fired"] = True
                        if self.callback:
                            self.callback(f"Reminder: {reminder['task']}!")
            time.sleep(10)

    def list_reminders(self) -> str:
        with self._lock:
            active = [r for r in self._reminders if not r["fired"]]
        if not active:
            return "No active reminders."
        lines = [f"- {r['task']} at {r['time'].strftime('%I:%M %p')}" for r in active]
        return "Your reminders:\n" + "\n".join(lines)
