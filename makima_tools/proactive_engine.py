"""
TOOL: Proactive Suggestion Engine
──────────────────────────────────────────────
Makima notices context and suggests actions
BEFORE the user asks. Hooks into your existing
media_observer.py, app_learner.py, battery_monitor.py.

USAGE in background_services.py or makima_assistant.py:
    from tools.proactive_engine import ProactiveEngine
    engine = ProactiveEngine(makima_instance)
    engine.start()   # runs in background thread

    # Or check manually:
    suggestion = engine.check_now(context)
    if suggestion:
        makima.speak(suggestion.message)
"""

import time
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any


# ── Config ────────────────────────────────────────────────────────────────────

CHECK_INTERVAL_SECONDS = 60      # check context every minute
SUGGESTION_COOLDOWN_SECONDS = 300  # don't repeat same suggestion within 5 min


# ── Suggestion dataclass ──────────────────────────────────────────────────────

@dataclass
class Suggestion:
    message: str           # what Makima says
    action: str            # what to auto-execute (optional)
    priority: int          # 1=low, 2=medium, 3=high
    trigger: str           # which rule fired
    auto_execute: bool = False   # execute without asking?

    def __str__(self):
        return f"[{self.priority}★] {self.message}"


# ── Rule definitions ──────────────────────────────────────────────────────────

class ProactiveEngine:

    def __init__(self, speak_fn: Callable = None, execute_fn: Callable = None):
        """
        speak_fn: your TTS function — speak_fn("Hello!")
        execute_fn: your command executor — execute_fn("play music")
        """
        self.speak = speak_fn or print
        self.execute = execute_fn
        self._running = False
        self._last_triggered: Dict[str, float] = {}
        self._context: Dict[str, Any] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Start background suggestion loop."""
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        print("[Proactive] Engine started")

    def stop(self):
        self._running = False

    def update_context(self, **kwargs):
        """
        Update Makima's awareness of current state.
        Call this from your existing observers.

        Examples:
            engine.update_context(active_app="vscode")
            engine.update_context(battery_percent=15)
            engine.update_context(is_in_call=True)
            engine.update_context(media_playing="Spotify")
        """
        self._context.update(kwargs)

    def check_now(self, extra_context: Dict = None) -> Optional[Suggestion]:
        """Manually trigger a context check. Returns suggestion or None."""
        if extra_context:
            self._context.update(extra_context)
        return self._evaluate_rules()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            suggestion = self._evaluate_rules()
            if suggestion:
                self._fire(suggestion)
            time.sleep(CHECK_INTERVAL_SECONDS)

    def _fire(self, suggestion: Suggestion):
        trigger = suggestion.trigger
        now = time.time()

        # Respect cooldown
        if now - self._last_triggered.get(trigger, 0) < SUGGESTION_COOLDOWN_SECONDS:
            return

        self._last_triggered[trigger] = now

        if suggestion.auto_execute and self.execute:
            self.execute(suggestion.action)
        else:
            self.speak(suggestion.message)

    # ── Rules ─────────────────────────────────────────────────────────────────

    def _evaluate_rules(self) -> Optional[Suggestion]:
        """Check all rules, return highest priority match."""
        ctx = self._context
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Mon, 6=Sun

        candidates = []

        # ── Battery rules ─────────────────────────────────────────────────────
        battery = ctx.get("battery_percent")
        is_charging = ctx.get("is_charging", True)
        if battery is not None and not is_charging:
            if battery <= 10:
                candidates.append(Suggestion(
                    message=f"Battery critically low at {battery}%. Plug in now!",
                    action="notify_battery_critical",
                    priority=3,
                    trigger="battery_critical"
                ))
            elif battery <= 20:
                candidates.append(Suggestion(
                    message=f"Battery at {battery}%. Want me to enable power saving mode?",
                    action="enable_power_saving",
                    priority=2,
                    trigger="battery_low"
                ))

        # ── Time-based rules ──────────────────────────────────────────────────
        if hour == 9 and weekday < 5:
            candidates.append(Suggestion(
                message="Good morning! Want your daily briefing?",
                action="daily_briefing",
                priority=2,
                trigger="morning_briefing"
            ))

        if hour == 12 and weekday < 5:
            candidates.append(Suggestion(
                message="It's noon. Taking a lunch break? I'll pause notifications.",
                action="focus_mode_off",
                priority=1,
                trigger="lunch_time"
            ))

        if hour == 17 and weekday < 5:
            candidates.append(Suggestion(
                message="End of work day. Want me to summarize what you accomplished today?",
                action="daily_summary",
                priority=2,
                trigger="end_of_day"
            ))

        if hour == 22:
            candidates.append(Suggestion(
                message="It's getting late. Want some sleep music or a wind-down reminder?",
                action="play chill music",
                priority=1,
                trigger="night_time"
            ))

        # ── App context rules ─────────────────────────────────────────────────
        active_app = ctx.get("active_app", "").lower()

        if "vscode" in active_app or "pycharm" in active_app or "cursor" in active_app:
            if not ctx.get("music_playing"):
                candidates.append(Suggestion(
                    message="Starting a coding session? Want me to play focus music?",
                    action="play focus music",
                    priority=1,
                    trigger="coding_no_music"
                ))

        if "zoom" in active_app or "teams" in active_app or "meet" in active_app:
            candidates.append(Suggestion(
                message="Looks like you're in a call. Going silent — I'll queue any messages.",
                action="silent_mode_on",
                priority=3,
                trigger="in_call",
                auto_execute=True
            ))

        if "excel" in active_app or "sheets" in active_app:
            candidates.append(Suggestion(
                message="Working on spreadsheets? I can help analyze or visualize your data.",
                action=None,
                priority=1,
                trigger="spreadsheet_open"
            ))

        # ── Idle detection ────────────────────────────────────────────────────
        last_active = ctx.get("last_activity_time")
        if last_active:
            idle_minutes = (time.time() - last_active) / 60
            if 20 <= idle_minutes <= 25:
                candidates.append(Suggestion(
                    message="You've been idle for 20 minutes. Taking a break? I can lock the screen.",
                    action="lock_screen",
                    priority=1,
                    trigger="idle_break"
                ))
            elif idle_minutes > 60:
                candidates.append(Suggestion(
                    message="You've been away over an hour. I'll pause background tasks to save resources.",
                    action="pause_background",
                    priority=2,
                    trigger="long_idle",
                    auto_execute=True
                ))

        # ── Focus mode rules ──────────────────────────────────────────────────
        in_focus = ctx.get("focus_mode_active", False)
        notification_count = ctx.get("pending_notifications", 0)
        if not in_focus and notification_count >= 5:
            candidates.append(Suggestion(
                message=f"You have {notification_count} pending notifications. Want focus mode to block them?",
                action="enable_focus_mode",
                priority=2,
                trigger="notification_overload"
            ))

        # ── Clipboard rules ───────────────────────────────────────────────────
        clipboard = ctx.get("clipboard_content", "")
        if clipboard:
            if "http" in clipboard and len(clipboard) < 200:
                candidates.append(Suggestion(
                    message="I see a URL in your clipboard. Want me to summarize that page?",
                    action=f"summarize {clipboard}",
                    priority=1,
                    trigger="clipboard_url"
                ))
            elif len(clipboard) > 500:
                candidates.append(Suggestion(
                    message="Looks like you copied a large block of text. Want me to summarize it?",
                    action="summarize_clipboard",
                    priority=1,
                    trigger="clipboard_large_text"
                ))

        # ── Return highest priority ───────────────────────────────────────────
        if candidates:
            return max(candidates, key=lambda s: s.priority)
        return None
