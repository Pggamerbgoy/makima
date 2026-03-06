"""
core/command_router.py
──────────────────────
Single, unified CommandRouter — all handlers in one class.
No monkey-patching. No backup files. No duplicates.
"""

import re
import logging
import threading
import os
import json
import time
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger("Makima.Router")


class CommandRouter:
    """
    Intent-based command router.
    Every handler lives here. Priority: PATTERNS -> learned skills -> AI chat.
    """

    # ── Pattern registry ───────────────────────────────────────────────────────
    PATTERNS = [
        # ── YouTube / Music (Prioritized to catch specific "play" intents) ────
        (r"play (.+?) on youtube",                          "_handle_yt_play"),
        (r"play (.+?) youtube",                             "_handle_yt_play"),
        (r"youtube play (.+)",                              "_handle_yt_play"),
        (r"youtube (?:search(?: for)?|dhoondo) (.+)",       "_handle_yt_search"),
        (r"(?:search|dhoondo) (.+?) (?:on|pe) youtube",     "_handle_yt_search"),
        (r"(?:put on|start) (.+?) (?:from|on) yt\b",       "_handle_yt_play"),
        (r"(?:set|rakho) (?:my |mera )?default (.+?) (?:to|pe|as) (.+)", "_handle_set_preference"),
        (r"(?:set|rakho) (?:my |mera )?(.+?) (?:to|pe|as) (.+)",         "_handle_set_preference"),
        
        # ── Tasks / To-Do ─────────────────────────────────────────────────────
        (r"add task[: ]+(.+)",                              "_task_add"),
        (r"add (?:a )?(?:to.?do|todo|task)[: ]+(.+)",      "_task_add"),
        (r"(?:complete|done|finish|mark done)[: ]+(.+)",    "_task_complete"),
        (r"delete task[: ]+(.+)",                           "_task_delete"),
        (r"(?:show|list|what(?:'s| are)(?: my)?) (?:tasks?|to.?dos?)", "_task_list"),
        (r"clear (?:all )?(?:completed )?tasks?",           "_task_clear_done"),

        # ── Memory ────────────────────────────────────────────────────────────
        (r"remember (?:that )?(.+)",                        "_handle_remember"),
        (r"yaad rakh (.+)",                                 "_handle_remember"),
        (r"(?:do you|kya tumhein) remember (.+)",           "_handle_recall"),
        (r"yaad hai (.+)",                                  "_handle_recall"),
        (r"memory stats|kitni yaadein",                     "_handle_memory_stats"),

        # ── Reminders ─────────────────────────────────────────────────────────
        (r"remind me to (.+?) (?:at|in) (.+)",              "_handle_reminder"),
        (r"set (?:a )?reminder (?:for )?(.+?) (?:at|in) (.+)", "_handle_reminder"),

        # ── Persona ───────────────────────────────────────────────────────────
        (r"switch to (makima|normal|date|coder) mode",      "_handle_persona"),
        (r"(makima|normal|date|coder) mode",                "_handle_persona"),

        # ── Skills ────────────────────────────────────────────────────────────
        (r"(?:learn|teach yourself|teach me) (?:how )?(?:to )?(.+)", "_handle_learn"),
        (r"(?:what skills|list skills|skills you (?:have|know))", "_handle_list_skills"),

        # ── App Learner ───────────────────────────────────────────────────────
        (r"learn (?:the )?app (.+)",                        "_handle_learn_app"),
        (r"how (?:do i|to) (.+?) in (.+)",                  "_handle_howto_in_app"),
        (r"how (?:do i|to) (.+)",                                "_handle_howto"),
        (r"next step",                                            "_handle_next_step"),
        (r"(?:stop|exit|cancel) (?:guide|workflow|walkthrough)",  "_handle_stop_guide"),
        (r"(?:tell me about|what is|describe) (?:the )?app (.+)","_handle_app_overview"),

        # ── App Control ───────────────────────────────────────────────────────
        (r"(?:open|launch|start|run|kholo) (.+)",           "_handle_open_app"),
        (r"(?:close|quit|kill|band karo) (.+)",             "_handle_close_app"),
        (r"scan apps",                                       "_handle_scan_apps"),

        # ── Music Controls ────────────────────────────────────────────────────
        (r"play (?:music|song|spotify)",                    "_handle_play"),
        (r"pause (?:music|spotify|youtube)?",               "_handle_pause"),
        (r"(?:music|dj|youtube) (?:skip|next)",             "_handle_next"),
        (r"(?:music|dj) (?:previous|prev)",                  "_handle_prev"),
        (r"what(?:'s| is) (?:currently )?playing",          "_handle_now_playing"),

        # ── Music DJ ──────────────────────────────────────────────────────────
        (r"play (?:some |me )?(?:focus|study|lofi|chill|hype|workout|gym|energy|party) (?:music|songs?|vibes?)", "_handle_dj_play_mood"),
        (r"play something (\w+)",                           "_handle_dj_play_mood"),

        # ── Web Music (Browser) ───────────────────────────────────────────────
        (r"play (.+) on (?:web )?(spotify|youtube|browser)", "_handle_play_web"),
        (r"(?:web )?(spotify|youtube) play (.+)",           "_handle_play_web"),

        # ── System ────────────────────────────────────────────────────────────
        (r"\bvolume (?:to |at )?(\d+)",               "_handle_volume_set"),
        (r"\bvolume up\b",                                  "_handle_volume_up"),
        (r"\bvolume down\b",                                "_handle_volume_down"),
        (r"\bmute\b",                                       "_handle_mute"),
        (r"\bunmute\b",                                     "_handle_unmute"),
        (r"lock (?:the )?(?:screen|pc|computer)",           "_handle_lock"),
        (r"take (?:a )?screenshot|screenshot",              "_handle_screenshot"),
        (r"(?:maximize|maximise) window",                   "_handle_maximize"),
        (r"(?:minimize|minimise) window",                   "_handle_minimize"),
        (r"close window",                                   "_handle_close_window"),
        (r"empty (?:recycle bin|trash)",                    "_handle_empty_trash"),
        (r"battery (?:status|level|percentage)?",           "_handle_battery"),
        (r"cpu usage",                                      "_handle_cpu"),
        (r"ram usage|memory usage",                         "_handle_ram"),

        # ── Web / Search ──────────────────────────────────────────────────────
        (r"\b(?:stop|cancel|stop pls)\b(?: (?:the )?(?:security )?scan)?", "_handle_stop_scan"),
        (r"(?:search(?: for)?|google|look up) (.+)",        "_handle_web_search"),
        (r"(?:download|get)(?: me)?(?: some)? (.+)",        "_handle_download_files"),

        # ── Code ──────────────────────────────────────────────────────────────
        (r"debug[: ]+(.+)",                                 "_handle_claude_debug"),
        (r"explain (?:this )?code[: ](.+)",                 "_handle_claude_explain"),
        (r"write code (?:to|for|that) (.+)",                "_handle_write_code"),
        (r"run code (.+)",                                  "_handle_run_code"),
        (r"(?:update|modify|change) your code in ([\w\/\\\.\-]+) to (.+)", "_handle_self_update"),

        # ── Calendar / Prefs ──────────────────────────────────────────────────
        (r"(?:my )?(?:today'?s? )?schedule(?: today)?",     "_handle_calendar_today"),
        (r"(?:what'?s? on )?my calendar|upcoming events?",  "_handle_calendar_upcoming"),
        (r"set (?:my )?(?:default )?([a-zA-Z0-9_\-]+) (?:app |platform )?to (.+)", "_handle_pref_set"),
        (r"set (?:my )?([a-zA-Z0-9_\-]+) preference to (.+)", "_handle_pref_set"),
        (r"what(?:'s| is) my (?:default )?([a-zA-Z0-9_\-]+)(?: preference)?[?]?",  "_handle_pref_get"),
        (r"(?:show|list) (?:my )?preferences",              "_handle_pref_list"),
        (r"clear (?:my )?(.+?) preference",                 "_handle_pref_clear"),

        # ── Mood ──────────────────────────────────────────────────────────────
        (r"how am i (?:feeling|doing)[?]?|my (?:mood|vibe)[?]?", "_handle_my_mood"),
        (r"i(?:'m| am) feeling (.+)",                       "_handle_set_mood"),

        # ── AI Backend ────────────────────────────────────────────────────────
        (r"use (?:ollama|local|offline)(?: mode)?",         "_handle_use_ollama"),
        (r"use (?:gemini|online|cloud)(?: mode)?",          "_handle_use_gemini"),
        (r"(?:which|what) (?:ai|model|brain)(?: are you using)?", "_handle_which_ai"),

        # ── Claude Coder ──────────────────────────────────────────────────────
        (r"claude (?:coder )?status|is claude (?:coder )?(?:active|on)",  "_handle_claude_status"),

        # ── Quantum Simulator ─────────────────────────────────────────────────
        (r"(?:quantum )?simulate (?:an )?investment of \$?([\d,]+) in (.+)", "_handle_qs_invest"),
        (r"(?:quantum )?simulate (?:a )?job change",        "_handle_qs_job"),

        # ── Background Services ───────────────────────────────────────────────
        (r"what did you do(?: in background)?|background activity|what happened", "_handle_bg_activity"),
        (r"(?:check|any|read) (?:new )?emails?",            "_handle_email_summary"),
        (r"background status|service status",               "_handle_bg_status"),

        # ── Focus Mode ────────────────────────────────────────────────────────
        (r"start focus|focus mode on",                      "_handle_focus_start"),
        (r"stop focus|focus mode off|end focus",            "_handle_focus_stop"),

        # ── Macros ────────────────────────────────────────────────────────────
        (r"start recording macro (.+)",                     "_handle_macro_record"),
        (r"stop recording",                                 "_handle_macro_stop"),
        (r"run macro (.+)",                                 "_handle_macro_run"),

        # ── Security & Cloud ──────────────────────────────────────────────────
        (r"quick scan",                                     "_handle_quick_scan"),
        (r"full scan|deep scan",                            "_handle_full_scan"),
        (r"scan (?:my )?downloads",                         "_handle_scan_downloads"),
        (r"sync (?:memory|brain) to cloud",                 "_handle_cloud_sync"),
        (r"upload (.+) to cloud",                           "_handle_cloud_upload"),

        # ── Session ───────────────────────────────────────────────────────────
        (r"summarize (?:this )?(?:session|conversation|chat)",        "_handle_summarize_session"),
        (r"(?:show|list) (?:past|old|archived|previous) sessions?",   "_handle_list_sessions"),

        # ── Utilities ─────────────────────────────────────────────────────────
        (r"what(?:'s| is) (?:the )?time|time (?:now|please)|what time is it",  "_handle_time"),
        (r"what(?:'s| is) (?:the )?(?:date|today)|today'?s date",              "_handle_date"),
        (r"status|health check",                             "_handle_status"),
        (r"help|what can you do",                           "_handle_help"),
        (r"good morning|good evening|good night|^(?:hello|hi|hey)(?:\s|$)",  "_handle_greeting"),
        (r"how (?:am i|are you)|learning report",           "_handle_report"),
        (r"what day is it|day today|which day",             "_handle_day"),
        (r"clear (?:history|chat)",                         "_handle_clear_history"),
        (r"stop speaking|shut up|be quiet|silence",         "_handle_stop_speech"),

        # ── Configuration ─────────────────────────────────────────────────────
        (r"set (?:api )?key (?:for )?([a-zA-Z0-9_]+) to (.+)", "_handle_config_set"),
        (r"set (?:my )?email (?:address|user) to (.+)",        "_handle_email_set"),
        (r"set (?:my )?email password to (.+)",                "_handle_email_pass_set"),
        (r"enable calendar",                                   "_handle_cal_enable"),
        (r"disable calendar",                                  "_handle_cal_disable"),
    ]

    def __init__(self, ai, memory):
        self.ai = ai
        self.memory = memory
        self._manager = None  # Reference to MakimaManager
        
        # Legacy attributes for compatibility with older subsystems
        self.skill_teacher = None
        self.app_learner = None
        self._calendar = None
        self._prefs = None
        self._music_dj = None
        self._services = None
        
        # Lazy-loaded subsystems (private cache)
        self._macros = None
        self._cloud = None
        self._decision_engine = None

    @property
    def decision_engine(self):
        if not self._decision_engine:
            from tools.decision_engine import DecisionEngine
            prefs = self._manager.prefs if self._manager else None
            self._decision_engine = DecisionEngine(prefs, self.ai)
        return self._decision_engine

    def _require_manager(self, attr: str = None):
        """Return the manager sub-component, or None if unavailable."""
        if not self._manager:
            return None
        if attr is None:
            return self._manager
        return getattr(self._manager, attr, None)

    def route(self, user_input: str) -> tuple[str, str]:
        """
        THE main routing method.
        Returns (response_text, handler_name).
        Priority: PATTERNS -> learned skills -> decision engine -> AI chat.
        """
        t0 = time.monotonic()
        text = user_input.strip()
        text_lower = text.lower()

        # 1. Pattern matching
        for pattern, handler_name in self.PATTERNS:
            try:
                m = re.search(pattern, text_lower, re.IGNORECASE)
                if m:
                    handler = getattr(self, handler_name, None)
                    if handler:
                        res = handler(m)
                        if res:
                            self._log_timing(t0, handler_name)
                            return res, handler_name
            except Exception as e:
                logger.debug(f"Pattern error {pattern!r}: {e}")

        # 2. Learned skills (via skill_teacher if available)
        if self.skill_teacher:
            try:
                res = self.skill_teacher.try_run_skill(text)
                if res:
                    self._log_timing(t0, "skill")
                    return res, "skill"
            except Exception as e:
                logger.debug(f"Skill teacher error: {e}")

        # 2.5 Decision Engine (Vague intents)
        try:
            intent = self.decision_engine.handle(text)
            if intent and isinstance(intent, dict) and intent.get("intent") != "unknown":
                result = self._dispatch_intent(intent)
                if result:
                    self._log_timing(t0, f"decision_engine:{intent.get('intent')}")
                    return result, f"decision_engine:{intent.get('intent')}"
        except Exception as e:
            logger.debug(f"Decision engine handle error: {e}")

        # 3. AI chat
        try:
            ctx = self.memory.build_memory_context(text) if self.memory else ""
            reply, _ = self.ai.chat(text, context=ctx)
            self._log_timing(t0, "ai_chat")
            return reply, "ai_chat"
        except Exception as e:
            logger.error(f"AI fallback failed: {e}")
            return "I'm having some trouble right now.", "error"

    def _log_timing(self, start: float, handler: str):
        """Log slow command routing (>2s) as warnings."""
        elapsed = time.monotonic() - start
        if elapsed > 2.0:
            logger.warning(f"Slow route: {handler} took {elapsed:.2f}s")
        else:
            logger.debug(f"Route: {handler} in {elapsed:.3f}s")

    def _dispatch_intent(self, intent: dict) -> Optional[str]:
        """Dispatch a parsed intent from the DecisionEngine to the appropriate handler."""
        intent_type = intent.get("intent", "unknown")

        if intent_type == "play_music":
            dj = self._get_dj()
            if dj:
                query = intent.get("genre") or intent.get("mood") or intent.get("artist")
                return dj.play(query) if query else dj.play()

        elif intent_type == "open_app":
            mgr = self._require_manager("apps")
            app_name = intent.get("app", "")
            if mgr and app_name:
                return mgr.open(app_name)

        elif intent_type == "web_search":
            mgr = self._require_manager("web")
            query = intent.get("query", "")
            if mgr and query:
                return mgr.search(query)

        elif intent_type == "set_reminder":
            task = intent.get("task", "")
            time_str = intent.get("time", "")
            if task:
                return f"Reminder set: {task}" + (f" at {time_str}" if time_str else ".")

        elif intent_type == "system_control":
            mgr = self._require_manager("system")
            action = intent.get("action", "")
            if mgr and action:
                return mgr._call(action, fallback=f"{action} done.")
                
        elif intent_type == "download_files":
            query = intent.get("query", "")
            file_type = intent.get("file_type", "")
            category = intent.get("category", "")
            if query:
                from core.auto_downloader import download_files_sync
                download_dir = os.path.join(
                    os.path.expanduser("~"), "Downloads",
                    "Makima_Downloads", query.replace(" ", "_")
                )
                os.makedirs(download_dir, exist_ok=True)

                def run_dl():
                    try:
                        download_files_sync(query, category, file_type, download_dir)
                    except Exception as e:
                        logger.error(f"AutoDownloader failed: {e}")

                threading.Thread(target=run_dl, daemon=True).start()
                return f"I've started searching and downloading '{query}' to your Makima Downloads folder. I'll handle it in the background."

        return None

    # ══════════════════════════════════════════════════════════════════════════
    # YOUTUBE / MUSIC / DJ
    # ══════════════════════════════════════════════════════════════════════════

    def _get_dj(self):
        """Get the MusicManager sub-component."""
        return self._manager.music if self._manager else None

    def _get_qs(self):
        """Get the DecisionSimulator sub-component."""
        return self._manager.simulator if self._manager else None

    def _handle_yt_play(self, m):
        music = self._require_manager("music")
        if music:
            return music.play(m.group(1).strip())
        return "Music system not ready."

    def _handle_yt_search(self, m):
        music = self._require_manager("music")
        if music:
            return music.search_web(m.group(1).strip())
        return "Music system not ready."

    def _handle_play(self, m):
        dj = self._get_dj()
        
        # Check explicit preferences first via Decision Engine
        res = self.decision_engine.decide("music")
        music = self._require_manager("music")
        if res.value == "youtube" and music:
            return music.play_web("", "youtube")
            
        return dj.play() if dj else "Music system not ready."

    def _handle_pause(self, m):
        dj = self._get_dj()
        if dj:
            # Try a real pause on Spotify first; fall back to stopping the DJ
            try:
                if dj._spotify:
                    dj._spotify.pause()
                    return "Paused."
            except Exception as e:
                logger.debug(f"Spotify pause error: {e}")
            try:
                if dj._dj and hasattr(dj._dj, "stop"):
                    dj._dj.stop()
                    return "Paused."
            except Exception as e:
                logger.debug(f"DJ stop error: {e}")
            return "Paused. (simulated)"
        return "No player found."

    def _handle_next(self, m):
        dj = self._get_dj()
        return dj.next() if dj else "Next."

    def _handle_prev(self, m):
        dj = self._get_dj()
        return dj.previous() if dj else "Previous."

    def _handle_now_playing(self, m):
        dj = self._get_dj()
        return dj.now_playing() if dj else "Nothing playing."

    def _handle_dj_play_mood(self, m):
        """Play music matching a detected mood keyword."""
        dj = self._get_dj()
        mood = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
        return dj.play(mood.strip()) if dj else "DJ not ready."

    def _handle_set_preference(self, m):
        prefs = self._require_manager("prefs")
        if prefs:
            category = m.group(1).strip().lower()
            value = m.group(2).strip()
            # Special case for browser names to match webbrowser expectations
            if "browser" in category:
                category = "browser"
            return prefs.set_explicit_preference(category, value)
        return "Preferences system not available."

    def _handle_play_web(self, m):
        """Handle 'play X on youtube/spotify' or 'youtube play X' patterns."""
        p1 = m.group(1).lower()
        p2 = m.group(2).lower() if len(m.groups()) > 1 else ""

        if p2 in ["spotify", "youtube", "browser"]:
            song, platform = p1, p2
        else:
            platform, song = p1, p2

        music = self._require_manager("music")
        if music:
            return music.play_web(song, platform)
        return "Music engine not available."

    # ══════════════════════════════════════════════════════════════════════════
    # TASKS (using internal tasks.json)
    # ══════════════════════════════════════════════════════════════════════════

    def _get_tasks(self) -> list:
        """Load task list from disk."""
        path = "makima_memory/tasks.json"
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Failed to load tasks: {e}")
        return []

    def _save_tasks(self, tasks: list):
        os.makedirs("makima_memory", exist_ok=True)
        with open("makima_memory/tasks.json", "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)

    def _get_reminders(self) -> list:
        """Load reminders from disk."""
        path = "makima_memory/reminders.json"
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Failed to load reminders: {e}")
        return []

    def _save_reminders(self, reminders: list):
        os.makedirs("makima_memory", exist_ok=True)
        with open("makima_memory/reminders.json", "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=2)

    def _task_add(self, m):
        title = m.group(1).strip()
        tasks = self._get_tasks()
        # Use max existing ID + 1 so IDs stay unique even after deletions
        next_id = max((t["id"] for t in tasks), default=0) + 1
        new_task = {"id": next_id, "title": title, "done": False, "created": datetime.now().isoformat()}
        tasks.append(new_task)
        self._save_tasks(tasks)
        return f"✅ Added task #{next_id}: {title}"

    def _task_list(self, m):
        tasks = self._get_tasks()
        if not tasks: return "No tasks found."
        lines = ["Your current tasks:"]
        for t in tasks:
            status = "[x]" if t['done'] else "[ ]"
            lines.append(f"{status} {t['id']}. {t['title']}")
        return "\n".join(lines)

    def _task_complete(self, m):
        query = m.group(1).strip().lower()
        tasks = self._get_tasks()
        found = False
        for t in tasks:
            if query in t['title'].lower() or query == str(t['id']):
                t['done'] = True
                found = True
        if found:
            self._save_tasks(tasks)
            return "Marked as done."
        return "Task not found."

    def _task_delete(self, m):
        query = m.group(1).strip().lower()
        tasks = self._get_tasks()
        new_tasks = [t for t in tasks if query not in t['title'].lower() and query != str(t['id'])]
        if len(new_tasks) < len(tasks):
            self._save_tasks(new_tasks)
            return "Task deleted."
        return "Task not found."

    def _task_clear_done(self, m):
        tasks = [t for t in self._get_tasks() if not t['done']]
        self._save_tasks(tasks)
        return "Cleared completed tasks."

    # ══════════════════════════════════════════════════════════════════════════
    # APPS
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_open_app(self, m):
        apps = self._require_manager("apps")
        return apps.open(m.group(1)) if apps else f"Opening {m.group(1)}."

    def _handle_close_app(self, m):
        apps = self._require_manager("apps")
        return apps.close(m.group(1)) if apps else f"Closing {m.group(1)}."

    def _handle_scan_apps(self, m):
        # Trigger help or scan
        return "Scanning for new apps..."

    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_unmute(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr._call("unmute", fallback="Unmuted.") if sys_mgr else "Unmuted."

    def _handle_volume_set(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr.set_volume(int(m.group(1))) if sys_mgr else "Volume set."

    def _handle_volume_up(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr.volume_up() if sys_mgr else "Volume up."

    def _handle_volume_down(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr.volume_down() if sys_mgr else "Volume down."

    def _handle_mute(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr.mute() if sys_mgr else "Muted."

    def _handle_lock(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr.lock_screen() if sys_mgr else "Locked."

    def _handle_screenshot(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr.screenshot() if sys_mgr else "Screenshot taken."

    def _handle_maximize(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr._call("maximize_window", fallback="Window maximized.") if sys_mgr else "Maximized."

    def _handle_minimize(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr._call("minimize_window", fallback="Window minimized.") if sys_mgr else "Minimized."

    def _handle_close_window(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr._call("close_window", fallback="Window closed.") if sys_mgr else "Closed."

    def _handle_empty_trash(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr._call("empty_recycle_bin", fallback="Trash emptied.") if sys_mgr else "Emptied."

    def _handle_cpu(self, m):
        sys_mgr = self._require_manager("system")
        if sys_mgr:
            return sys_mgr._call("cpu_usage", fallback="CPU usage unavailable.")
        return "System manager not linked."

    def _handle_ram(self, m):
        sys_mgr = self._require_manager("system")
        if sys_mgr:
            return sys_mgr._call("ram_usage", fallback="RAM usage unavailable.")
        return "System manager not linked."

    def _handle_battery(self, m):
        try:
            import psutil
            batt = psutil.sensors_battery()
            if batt:
                plug = " (plugged in)" if batt.power_plugged else ""
                return f"Battery is at {batt.percent}%{plug}."
            return "Battery info not available on this system."
        except Exception as e:
            logger.debug(f"Battery check failed: {e}")
            return "Battery status unavailable."

    # ══════════════════════════════════════════════════════════════════════════
    # MEMORY / REMINDERS / SKILLS / HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_remember(self, m):
        if self.memory:
            self.memory.save_note(m.group(1))
            return f"Noted. I'll remember that."
        return "Memory system not available."

    def _handle_recall(self, m):
        if self.memory:
            res = self.memory.recall_note(m.group(1))
            if res: return f"I remember: {res}"
        return "I don't remember anything about that."

    def _handle_memory_stats(self, m):
        if self.memory:
            return self.memory.format_stats()
        return "Memory system not available."

    def _handle_reminder(self, m):
        task = m.group(1).strip()
        time_str = m.group(2).strip()
        reminders = self._get_reminders()
        reminder = {
            "id": max((r["id"] for r in reminders), default=0) + 1,
            "task": task,
            "time": time_str,
            "created": datetime.now().isoformat(),
            "done": False,
        }
        reminders.append(reminder)
        self._save_reminders(reminders)
        return f"⏰ Reminder set: '{task}' at {time_str}."

    def _handle_persona(self, m):
        return self.ai.set_persona(m.group(1))

    def _handle_learn(self, m):
        if self.skill_teacher: return self.skill_teacher.teach(m.group(1))
        return "I'm ready to learn. Tell me what to do."

    def _handle_list_skills(self, m):
        if self.skill_teacher: return self.skill_teacher.list_skills()
        return "I have a few built-in skills."

    # ══════════════════════════════════════════════════════════════════════════
    # WEB / CODE
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_web_search(self, m):
        web = self._require_manager("web")
        return web.search(m.group(1)) if web else f"Searching for {m.group(1)}."

    def _handle_download_files(self, m):
        query = m.group(1).strip()
        if not query:
            return "What do you want me to download?"
            
        import threading
        import os
        from core.auto_downloader import download_files_sync
        
        # Explicit fallback triggers all types of downloads loosely
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "Makima_Downloads", query.replace(" ", "_"))
        os.makedirs(download_dir, exist_ok=True)
        
        def run_dl():
            import logging
            try:
                download_files_sync(query, "", "", download_dir)
            except Exception as e:
                logging.getLogger("Makima.CommandRouter").error(f"AutoDownloader failed: {e}")
        
        threading.Thread(target=run_dl, daemon=True).start()
        return f"I've started searching and downloading '{query}' to your Makima Downloads folder."

    def _handle_stop_scan(self, m):
        security = self._require_manager("security")
        if security:
            return security.stop_scan()
        return "Security system not available."

    def _handle_claude_debug(self, m):
        return self.ai.code_chat(f"Debug this: {m.group(1)}")

    def _handle_claude_explain(self, m):
        return self.ai.code_chat(f"Explain this: {m.group(1)}")

    def _handle_write_code(self, m):
        # Use Claude Coder if available, else fallback to AI chat
        if self._manager and self._manager._claude_coder and self._manager._claude_coder.available:
            return self._manager._claude_coder.handle_code_task(f"Write code to {m.group(1)}")
        return self.ai.code_chat(f"Write Python code to: {m.group(1)}")

    def _handle_run_code(self, m):
        return "I cannot execute arbitrary code yet for safety reasons."

    # ══════════════════════════════════════════════════════════════════════════
    # CALENDAR / PREFS / MOOD
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_calendar_today(self, m):
        """Show today's schedule from the calendar subsystem."""
        briefing = self._require_manager("briefing")
        if briefing:
            try:
                return briefing.deliver(style="quick")
            except Exception as e:
                logger.debug(f"Calendar today error: {e}")
        return "Calendar service is not configured. Enable it with 'enable calendar'."

    def _handle_calendar_upcoming(self, m):
        """Show upcoming events from the calendar subsystem."""
        briefing = self._require_manager("briefing")
        if briefing:
            try:
                return briefing.deliver(style="full")
            except Exception as e:
                logger.debug(f"Calendar upcoming error: {e}")
        return "Calendar service is not configured. Enable it with 'enable calendar'."

    def _handle_pref_set(self, m):
        """Set a user preference."""
        prefs = self._require_manager("prefs")
        if prefs:
            return prefs.set_explicit_preference(m.group(1).strip(), m.group(2).strip())
        return f"Set {m.group(1)} preference to {m.group(2)}."

    def _handle_pref_get(self, m):
        """Get a user preference value."""
        prefs = self._require_manager("prefs")
        if prefs:
            val = prefs.get_preference(m.group(1).strip())
            if val:
                return f"Your {m.group(1)} preference is: {val}"
            return f"No preference set for {m.group(1)}."
        return f"Preferences system not available."

    def _handle_pref_list(self, m):
        """List all preferences."""
        prefs = self._require_manager("prefs")
        if prefs:
            return prefs.list_preferences()
        return "Preferences system not available."

    def _handle_pref_clear(self, m):
        """Clear a specific preference."""
        prefs = self._require_manager("prefs")
        if prefs:
            return prefs.clear_preference(m.group(1).strip())
        return f"Cleared {m.group(1)} preference."

    def _handle_my_mood(self, m):
        """Show current mood analytics."""
        mood = self._require_manager("mood")
        if mood:
            try:
                # get_report() is an alias for get_session_summary()
                report = mood.get_report()
                if isinstance(report, str):
                    return report
                return str(report)
            except AttributeError:
                # Fallback: call the real method directly
                try:
                    return mood.get_session_summary()
                except Exception:
                    pass
            except Exception as e:
                logger.debug(f"Mood report error: {e}")
        return "Mood tracking is available. Tell me how you're feeling!"

    def _handle_set_mood(self, m):
        """Record the user's current mood."""
        mood = self._require_manager("mood")
        feeling = m.group(1).strip()
        if mood:
            try:
                mood.analyze(f"I'm feeling {feeling}")
            except Exception as e:
                logger.debug(f"Mood set error: {e}")
        return f"Noted. You're feeling {feeling}."

    # ── AI Backend ────────────────────────────────────────────────────────────

    def _handle_use_ollama(self, m):
        self.ai.gemini_enabled = False
        return "Switched to local brain (Ollama)."

    def _handle_use_gemini(self, m):
        self.ai._init_gemini()
        return "Switched to Gemini."

    def _handle_which_ai(self, m):
        return "I'm using Gemini right now." if self.ai.gemini_enabled else "I'm using Ollama."

    # ══════════════════════════════════════════════════════════════════════════
    # CLAUDE / QS / BG
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_claude_status(self, m):
        return "Claude Coder is standing by."

    def _handle_qs_invest(self, m):
        qs = self._get_qs()
        if qs:
            # qs is the DecisionSimulator wrapper from MakimaManager
            return qs.analyze(f"invest ${m.group(1)} in {m.group(2)}", 
                            context={"amount": float(m.group(1).replace(",","")), "asset": m.group(2)})
        return "Quantum Simulator not available."

    def _handle_qs_job(self, m):
        qs = self._get_qs()
        if qs:
            return qs.analyze("should I change jobs")
        return "Quantum Simulator not available."

    def _handle_bg_activity(self, m):
        services = self._require_manager("services")
        if services:
            return services.what_did_you_do()
        return "Background services are not active."

    def _handle_email_summary(self, m):
        services = self._require_manager("services")
        if services:
            return services.email_summary()
        return "Background email service is not active."

    def _handle_bg_status(self, m):
        services = self._require_manager("services")
        if services:
            return services.full_status()
        return "Background services are not active."

    # ══════════════════════════════════════════════════════════════════════════
    # RESTORED HANDLERS (Macros, Focus, Security, Cloud, Self-Update)
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_focus_start(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr.focus_mode(True) if sys_mgr else "Focus mode on."

    def _handle_focus_stop(self, m):
        sys_mgr = self._require_manager("system")
        return sys_mgr.focus_mode(False) if sys_mgr else "Focus mode off."

    def _handle_macro_record(self, m):
        if not self._macros:
            try:
                from systems.macros import MacroSystem
                self._macros = MacroSystem()
            except Exception as e:
                logger.debug(f"Macro init failed: {e}")
                return "Macro system unavailable."
        return self._macros.start_recording(m.group(1))

    def _handle_macro_stop(self, m):
        if self._macros: return self._macros.stop_recording()
        return "No macro recording active."

    def _handle_macro_run(self, m):
        if not self._macros:
            try:
                from systems.macros import MacroSystem
                self._macros = MacroSystem()
            except Exception as e:
                logger.debug(f"Macro init failed: {e}")
                return "Macro system unavailable."
        return self._macros.run_macro(m.group(1))

    def _handle_quick_scan(self, m):
        security = self._require_manager("security")
        if security:
            return security.quick_scan()
        return "Security manager not available."

    def _handle_full_scan(self, m):
        security = self._require_manager("security")
        if security:
            return security.full_scan()
        return "Security manager not available."

    def _handle_scan_downloads(self, m):
        security = self._require_manager("security")
        if security:
            return security.scan_downloads()
        return "Security manager not available."

    def _handle_cloud_sync(self, m):
        if not self._cloud:
            try:
                from cloud.cloud_manager import CloudManager
                self._cloud = CloudManager()
            except Exception as e:
                logger.debug(f"Cloud init failed: {e}")
                return "Cloud manager unavailable."
        return self._cloud.sync_now()

    def _handle_cloud_upload(self, m):
        if not self._cloud:
            try:
                from cloud.cloud_manager import CloudManager
                self._cloud = CloudManager()
            except Exception as e:
                logger.debug(f"Cloud init failed: {e}")
                return "Cloud manager unavailable."
        return self._cloud.upload(m.group(1))

    def _handle_self_update(self, m):
        try:
            from systems.self_updater import SelfUpdater
            updater = SelfUpdater(self.ai)
            return updater.update_file(m.group(1), m.group(2))
        except Exception as e:
            return f"Update failed: {e}"

    def _handle_greeting(self, m):
        greeting = m.group(0).lower()
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        if "morning" in greeting:
            briefing = self._require_manager("briefing")
            if briefing:
                try:
                    return briefing.deliver(style="quick")
                except Exception as e:
                    logger.debug(f"Briefing error: {e}")
            return f"Good morning! It's {time_str} — ready when you are."
        elif "evening" in greeting:
            return f"Good evening! It's {time_str}. How was your day?"
        return "Good night. Rest well — I'll be here when you're back."

    def _handle_report(self, m):
        if self.memory:
            stats = self.memory.get_stats()
            return (f"You've had {stats.get('total_entries',0)} interactions with me, "
                    f"and I have {stats.get('notes_count',0)} saved notes about you.")
        return "I don't have access to my memory stats right now."

    def _handle_day(self, m):
        return f"Today is {datetime.now().strftime('%A')}."

    def _handle_clear_history(self, m):
        self.ai.clear_history()
        return "Conversation history cleared."

    def _handle_stop_speech(self, m):
        return "Stopping."

    # ── Configuration ─────────────────────────────────────────────────────────

    def _handle_config_set(self, m):
        key_map = {
            "gemini": "GEMINI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "ollama": "OLLAMA_URL",
        }
        raw_key = m.group(1).lower()
        key = key_map.get(raw_key, raw_key.upper())
        val = m.group(2).strip()
        mgr = self._require_manager()
        if mgr:
            return mgr.update_credential(key, val)
        return "Manager not available."

    def _handle_email_set(self, m):
        mgr = self._require_manager()
        if mgr:
            return mgr.update_credential("EMAIL_ADDRESS", m.group(1).strip())
        return "Manager not available."

    def _handle_email_pass_set(self, m):
        mgr = self._require_manager()
        if mgr:
            return mgr.update_credential("EMAIL_PASSWORD", m.group(1).strip())
        return "Manager not available."

    def _handle_cal_enable(self, m):
        if self._manager: self._manager.update_credential("CALENDAR_ENABLED", "1")
        return "Calendar enabled (restart may be required for full load)."

    def _handle_cal_disable(self, m):
        if self._manager: self._manager.update_credential("CALENDAR_ENABLED", "0")
        return "Calendar disabled."



    # ══════════════════════════════════════════════════════════════════════════
    # SESSION / UTILS
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_summarize_session(self, m):
        """Summarize the current conversation session."""
        summarizer = self._require_manager("summarizer")
        if summarizer:
            try:
                summary = summarizer.summarize_current()
                if summary:
                    return summary
            except Exception as e:
                logger.debug(f"Session summarize error: {e}")
        # Fallback: use AI to summarize history
        if self.ai and self.ai.conversation_history:
            try:
                reply, _ = self.ai.chat("Summarize our conversation so far in a few bullet points.")
                return reply
            except Exception:
                pass
        return "No conversation history to summarize."

    def _handle_list_sessions(self, m):
        """List archived session summaries."""
        summarizer = self._require_manager("summarizer")
        if summarizer:
            try:
                sessions = summarizer.list_sessions()
                if sessions:
                    return sessions
            except Exception as e:
                logger.debug(f"List sessions error: {e}")
        return "No archived sessions found."

    def _handle_time(self, m):
        return f"It's {datetime.now().strftime('%H:%M')}."

    def _handle_date(self, m):
        return f"Today is {datetime.now().strftime('%B %d, %Y')}."

    def _handle_status(self, m):
        mgr = self._require_manager()
        return mgr.status_str() if mgr else "System status: OK"

    def _handle_help(self, m):
        return (
            "Here's what I can do:\n\n"
            "🎵 **Music** — play/pause/skip, YouTube, Spotify, DJ moods\n"
            "   e.g. *play lofi music*, *play Bohemian Rhapsody on youtube*\n\n"
            "📝 **Tasks** — add/complete/delete/list to-dos\n"
            "   e.g. *add task finish report*, *show tasks*\n\n"
            "⏰ **Reminders** — set timed reminders\n"
            "   e.g. *remind me to call mom at 6pm*\n\n"
            "📱 **Apps** — open or close any app\n"
            "   e.g. *open Chrome*, *close Spotify*\n\n"
            "🔊 **System** — volume, brightness, screenshot, lock screen\n"
            "   e.g. *volume 50*, *take a screenshot*\n\n"
            "🌐 **Web** — search the web, download files\n"
            "   e.g. *search latest AI news*, *download cyberpunk wallpapers*\n\n"
            "🧠 **Memory** — remember facts, recall notes\n"
            "   e.g. *remember my API key is XYZ*, *do you remember my API key*\n\n"
            "🎭 **Mood** — track your emotional state\n"
            "   e.g. *I'm feeling stressed*, *how am I feeling*\n\n"
            "💡 **AI Modes** — switch personas or AI backend\n"
            "   e.g. *switch to coder mode*, *use gemini*, *use ollama*\n\n"
            "📊 **Analysis** — simulate investment/job decisions\n"
            "   e.g. *simulate an investment of $5000 in Bitcoin*"
        )
