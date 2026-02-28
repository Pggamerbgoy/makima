"""
systems/health_tracker.py

Health & Habit Tracker
───────────────────────
Makima monitors your health and wellbeing silently:
  - Screen time tracking per app
  - Water/hydration reminders every X minutes
  - Posture / break reminders (20-20-20 rule)
  - Daily step / activity check-ins
  - Habit streaks (track custom habits)
  - Daily health summary

Commands:
  "Start health tracking"
  "Drink water reminder every 30 minutes"
  "Take a break reminder"
  "How long have I been on screen?"
  "Health summary"
  "Log habit: [habit name]"
  "My habits"
  "How's my screen time today?"
  "Set break reminder every [X] minutes"
  "Disable water reminders"
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, date, timedelta
from typing import Callable, Optional

logger = logging.getLogger("Makima.HealthTracker")

HEALTH_DATA_FILE = "health_data.json"
HABITS_FILE = "habits.json"


class HealthTracker:
    """Silent background health monitoring with smart reminders."""

    def __init__(self, speak_callback: Callable):
        self.speak = speak_callback
        self._running = False

        # Screen time
        self._session_start = time.time()
        self._screen_time_today: float = self._load_today_screen_time()

        # Reminders
        self._water_interval: Optional[int] = 30 * 60   # seconds
        self._break_interval: Optional[int] = 45 * 60   # seconds (20-20-20)
        self._last_water = time.time()
        self._last_break = time.time()
        self._water_enabled = True
        self._break_enabled = True

        # Habits
        self._habits: dict = self._load_habits()

        # Start background thread
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_today_screen_time(self) -> float:
        today = str(date.today())
        if os.path.exists(HEALTH_DATA_FILE):
            try:
                with open(HEALTH_DATA_FILE) as f:
                    data = json.load(f)
                return data.get("screen_time", {}).get(today, 0.0)
            except Exception:
                pass
        return 0.0

    def _save_screen_time(self):
        today = str(date.today())
        data = {}
        if os.path.exists(HEALTH_DATA_FILE):
            try:
                with open(HEALTH_DATA_FILE) as f:
                    data = json.load(f)
            except Exception:
                pass
        data.setdefault("screen_time", {})[today] = self._screen_time_today
        with open(HEALTH_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _load_habits(self) -> dict:
        if os.path.exists(HABITS_FILE):
            try:
                with open(HABITS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_habits(self):
        with open(HABITS_FILE, "w") as f:
            json.dump(self._habits, f, indent=2, ensure_ascii=False)

    # ── Monitor Loop ──────────────────────────────────────────────────────────

    def _monitor_loop(self):
        logger.info("💚 Health tracker running silently.")
        tick_interval = 60  # check every minute

        while True:
            now = time.time()

            # Update screen time
            self._screen_time_today += tick_interval
            self._save_screen_time()

            # Water reminder
            if self._water_enabled and self._water_interval:
                if now - self._last_water >= self._water_interval:
                    self.speak("💧 Hydration reminder! Time to drink some water.")
                    self._last_water = now

            # Break reminder (20-20-20 rule: every 20 min, look 20ft away for 20 sec)
            if self._break_enabled and self._break_interval:
                if now - self._last_break >= self._break_interval:
                    mins = int(self._screen_time_today / 60)
                    self.speak(
                        f"👁 Eye strain alert! You've been on screen for "
                        f"{self._format_time(self._screen_time_today)}. "
                        f"Look away for 20 seconds and stretch."
                    )
                    self._last_break = now

            # Long session warning (> 2 hours straight)
            session_duration = now - self._session_start
            if session_duration > 2 * 3600 and int(session_duration) % 3600 == 0:
                self.speak(
                    "🧘 You've been working for over 2 hours straight. "
                    "Consider taking a proper 5-10 minute break."
                )

            time.sleep(tick_interval)

    # ── Screen Time ───────────────────────────────────────────────────────────

    def get_screen_time(self) -> str:
        today = self._format_time(self._screen_time_today)
        session = self._format_time(time.time() - self._session_start)
        return (
            f"📊 Screen time today: {today}. "
            f"Current session: {session}."
        )

    def _format_time(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m"
        return f"{m}m"

    # ── Reminders ─────────────────────────────────────────────────────────────

    def set_water_reminder(self, minutes: int) -> str:
        self._water_interval = minutes * 60
        self._water_enabled = True
        self._last_water = time.time()
        return f"💧 I'll remind you to drink water every {minutes} minutes."

    def disable_water_reminder(self) -> str:
        self._water_enabled = False
        return "Water reminders disabled."

    def set_break_reminder(self, minutes: int) -> str:
        self._break_interval = minutes * 60
        self._break_enabled = True
        self._last_break = time.time()
        return f"⏰ Break reminder set every {minutes} minutes."

    def disable_break_reminder(self) -> str:
        self._break_enabled = False
        return "Break reminders disabled."

    def take_break_now(self) -> str:
        self._last_break = time.time()
        self._session_start = time.time()  # Reset session
        return "👏 Great! Enjoy your break. I'll remind you again later."

    # ── Habit Tracking ────────────────────────────────────────────────────────

    def log_habit(self, habit_name: str) -> str:
        today = str(date.today())
        habit = self._habits.setdefault(habit_name.lower(), {
            "name": habit_name,
            "log": [],
            "streak": 0,
            "longest_streak": 0,
        })

        log = habit["log"]
        if today in log:
            return f"You already logged '{habit_name}' today! Keep it up! 🔥"

        log.append(today)
        # Keep only last 365 days
        habit["log"] = log[-365:]

        # Calculate streak
        streak = 0
        check_date = date.today()
        log_set = set(log)
        while str(check_date) in log_set:
            streak += 1
            check_date -= timedelta(days=1)

        habit["streak"] = streak
        habit["longest_streak"] = max(streak, habit.get("longest_streak", 0))
        self._save_habits()

        streak_msg = f" 🔥 {streak} day streak!" if streak > 1 else " Keep going!"
        return f"Logged '{habit_name}' for today!{streak_msg}"

    def get_habits(self) -> str:
        if not self._habits:
            return "No habits tracked yet. Say 'log habit: [name]' to start tracking."
        today = str(date.today())
        lines = ["Your habits:"]
        for name, data in self._habits.items():
            done_today = "✅" if today in data["log"] else "⬜"
            streak = data.get("streak", 0)
            streak_str = f" 🔥 {streak} day streak" if streak > 1 else ""
            lines.append(f"  {done_today} {data['name']}{streak_str}")
        return "\n".join(lines)

    def delete_habit(self, name: str) -> str:
        if name.lower() in self._habits:
            del self._habits[name.lower()]
            self._save_habits()
            return f"Habit '{name}' deleted."
        return f"Habit '{name}' not found."

    # ── Health Summary ────────────────────────────────────────────────────────

    def health_summary(self) -> str:
        today = str(date.today())
        screen = self._format_time(self._screen_time_today)
        session = self._format_time(time.time() - self._session_start)
        habits_done = sum(1 for h in self._habits.values() if today in h.get("log", []))
        habits_total = len(self._habits)

        parts = [
            f"💚 Health Summary for {datetime.now().strftime('%A, %b %d')}:",
            f"  📱 Screen time: {screen} total, {session} this session",
        ]

        if habits_total > 0:
            parts.append(f"  ✅ Habits: {habits_done}/{habits_total} done today")

        if self._water_enabled:
            next_water = max(0, self._water_interval - (time.time() - self._last_water))
            parts.append(f"  💧 Next water reminder in {self._format_time(next_water)}")

        return "\n".join(parts)
