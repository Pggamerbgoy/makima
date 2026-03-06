"""
core/makima_manager.py
──────────────────────
MakimaManager — Central Nervous System

Single entry point for every Makima capability.
All front-ends (voice, UI, web dashboard) only call manager methods.

Architecture:
    MakimaManager
    ├── ai           → AIHandler        (Gemini / Ollama)
    ├── memory       → EternalMemory    (persistent long-term memory)
    ├── router       → CommandRouter    (intent matching + AI fallback)
    ├── music        → MusicManager     (Spotify, MusicDJ, YouTube)
    ├── apps         → AppManager       (open/close/toggle)
    ├── system       → SystemManager    (volume, brightness, screenshot)
    ├── agents       → AgentManager     (V4 swarm)
    ├── prefs        → PreferencesManager
    ├── tools        → ToolsManager     (cache, intent, file finder)
    ├── simulator    → DecisionSimulator (Quantum Monte Carlo)
    ├── web          → WebSearchManager
    ├── tasks        → handled via CommandRouter._task_*
    ├── mood         → MoodTracker
    ├── briefing     → DailyBriefing
    └── summarizer   → SessionSummarizer
"""

import logging
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger("Makima.Manager")


# ── Optional feature imports ──────────────────────────────────────────────────

def _try_import(module, cls, **kwargs):
    try:
        import importlib
        mod = importlib.import_module(module)
        klass = getattr(mod, cls)
        return klass(**kwargs) if kwargs else klass()
    except Exception as e:
        logger.debug(f"{cls} unavailable: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SUB-MANAGERS
# ══════════════════════════════════════════════════════════════════════════════

class MusicManager:
    """Owns Spotify + MusicDJ + WebMusic (since User wants to keep Web)."""

    def __init__(self, speak_fn: Callable = None, prefs=None):
        self._speak = speak_fn or print
        self._prefs = prefs
        self._dj         = _try_import("systems.music_dj",      "MusicDJ")
        self._spotify    = _try_import("systems.spotify_control","SpotifyControl")
        self._youtube    = _try_import("systems.youtube_player", "YouTubePlayer")
        self._web_music  = _try_import("systems.web_music",      "WebMusic", prefs=self._prefs)

        if self._dj and self._youtube:
            self._dj.yt = self._youtube

    def search_web(self, query: str) -> str:
        """Explicitly search on YouTube browser."""
        if self._web_music:
            return self._web_music.search_youtube(query)
        return "Web system unavailable."

    def play_web(self, query: str, platform: str = "any") -> str:
        """Explicitly open music in the browser with DIRECT PLAY priority."""
        if not self._web_music:
            return "Web music system is not available."

        # SMART SEARCH: Try to find a direct video link first for YouTube/Any
        if platform in ["any", "youtube", "browser"] and self._youtube:
            try:
                logger.info(f"Attempting smart direct-play search for: {query}")
                results = self._youtube.search(query, max_results=1)
                if results:
                    track = results[0]
                    return self._web_music.open_url(track['url'], track['title'])
            except Exception as e:
                logger.debug(f"Smart search error: {e}")

        # Fallback to standard web search
        if platform == "spotify":
            return self._web_music.play_web_spotify(query)
        elif platform == "youtube":
            return self._web_music.search_youtube(query)
        else:
            return self._web_music.play_any(query)

    def play(self, query: str = None) -> str:
        # Default behavior: User requested WEB PRIORITY
        if not query:
            if self._spotify:
                try: 
                    self._spotify.play()
                    return "Resuming Spotify."
                except Exception as e:
                    logger.debug(f"Spotify resume failed: {e}")
            return "What would you like to hear?"

        # 1. Use consolidated Web Priority logic
        return self.play_web(query)

    def next(self) -> str:
        if self._spotify:
            try: self._spotify.next_track(); return "Skipped."
            except Exception: pass
        return "Skipped. (simulated)"

    def previous(self) -> str:
        if self._spotify:
            try: self._spotify.previous_track(); return "Previous track."
            except Exception: pass
        return "Previous. (simulated)"

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        if self._spotify:
            try: self._spotify.set_volume(level); return f"Spotify volume: {level}%."
            except Exception: pass
        return f"Volume set to {level}%. (simulated)"

    def now_playing(self) -> str:
        if self._spotify:
            try:
                info = self._spotify.current_track()
                if info:
                    return f"Now playing: {info.get('name','?')} by {info.get('artist','?')}"
            except Exception: pass
        return "Nothing playing."

    @property
    def ready(self) -> bool:
        return any([self._dj, self._spotify, self._web_music])


class AppManager:
    def __init__(self):
        self._ctrl = _try_import("systems.app_control", "AppControl")

    def open(self, app: str) -> str:
        if self._ctrl:
            try:
                r = self._ctrl.open(app)
                # FIXED: Preserve my consistency fix for return types
                if isinstance(r, dict):
                    return r.get("message", f"Opening {app}.")
                return str(r)
            except Exception as e:
                logger.warning(f"AppManager.open failed: {e}")
                return f"Error opening {app}."
        return f"Opening {app}. (AppControl not loaded)"

    def close(self, app: str) -> str:
        if self._ctrl:
            try:
                r = self._ctrl.close(app)
                if isinstance(r, dict):
                    return r.get("message", f"Closing {app}.")
                return str(r)
            except Exception as e:
                logger.warning(f"AppManager.close failed: {e}")
                return f"Error closing {app}."
        return f"Closing {app}. (AppControl not loaded)"

    def toggle(self, app: str) -> str:
        if self._ctrl:
            try:
                r = self._ctrl.toggle(app)
                if isinstance(r, dict):
                    return r.get("message", f"Toggled {app}.")
                return str(r)
            except Exception:
                pass
        return f"Toggled {app}. (simulated)"

    def is_running(self, app: str) -> bool:
        return self._ctrl.is_running(app) if self._ctrl else False

    @property
    def ready(self) -> bool:
        return self._ctrl is not None


class SystemManager:
    def __init__(self):
        self._ctrl = _try_import("systems.system_commands", "SystemCommands")

    def _call(self, method: str, *args, fallback: str = "Done. (simulated)") -> str:
        if self._ctrl and hasattr(self._ctrl, method):
            try:
                r = getattr(self._ctrl, method)(*args)
                return str(r) if r else fallback
            except Exception as e:
                logger.debug(f"SystemManager.{method}: {e}")
        return fallback

    def volume_up(self, amt: int = 10) -> str:
        return self._call("volume_up", amt, fallback=f"Volume up {amt}%. (simulated)")

    def volume_down(self, amt: int = 10) -> str:
        return self._call("volume_down", amt, fallback=f"Volume down {amt}%. (simulated)")

    def set_volume(self, level: int) -> str:
        return self._call("set_volume", level, fallback=f"Volume {level}%. (simulated)")

    def mute(self) -> str:
        return self._call("mute", fallback="Muted. (simulated)")

    def set_brightness(self, level: int) -> str:
        return self._call("set_brightness", level, fallback=f"Brightness {level}%. (simulated)")

    def screenshot(self, path: str = None) -> str:
        return self._call("screenshot", fallback="Screenshot taken. (simulated)")

    def lock_screen(self) -> str:
        return self._call("lock_screen", fallback="Screen locked. (simulated)")

    def focus_mode(self, enable: bool = True) -> str:
        method = "enable_focus_mode" if enable else "disable_focus_mode"
        label  = "enabled" if enable else "disabled"
        return self._call(method, fallback=f"Focus mode {label}. (simulated)")

    @property
    def ready(self) -> bool:
        return self._ctrl is not None


class AgentManager:
    """Owns the V4 agent swarm."""

    def __init__(self, ai_handler=None, memory=None, on_conflict=None):
        self._ai     = ai_handler
        self._memory = memory
        self._on_conflict = on_conflict
        self._v4     = None
        self._init()

    def _init(self):
        try:
            # We try to import MakimaV4 if available
            from agents.v4_agent import MakimaV4 # Path might vary in makima_fixed
            self._v4 = MakimaV4(ai_handler=self._ai, on_conflict=self._on_conflict)
            logger.info("🤖 AgentManager ready")
        except Exception:
            try:
                from Makima_v4.main import MakimaV4
                self._v4 = MakimaV4(ai_handler=self._ai, on_conflict=self._on_conflict)
                logger.info("🤖 AgentManager ready (V4 swarm)")
            except Exception as e:
                logger.debug(f"AgentManager init failed: {e}")

    def run(self, task: str) -> Optional[str]:
        if self._v4:
            try:
                result = self._v4.process(task)
                return result if isinstance(result, str) else str(result)
            except Exception as e:
                logger.warning(f"Agent swarm failed: {e}")
        return None

    @property
    def ready(self) -> bool:
        return self._v4 is not None


class WebSearchManager:
    def __init__(self, ai_handler=None):
        self._agent = _try_import("agents.web_agent", "WebAgent", ai=ai_handler)

    def search(self, query: str) -> str:
        if self._agent:
            try:
                return self._agent.search(query)
            except Exception as e:
                logger.debug(f"Web search failed: {e}")
        return f"Web search unavailable. Query was: {query}"

    @property
    def ready(self) -> bool:
        return self._agent is not None


class DecisionSimulator:
    def __init__(self):
        self._qs = _try_import("systems.quantum_simulator", "QuantumSimulator", verbose=False)

    def analyze(self, question: str, context: Dict = None) -> str:
        if not self._qs:
            return "Decision simulator not available."
        context = context or {}
        q = question.lower()
        try:
            if any(w in q for w in ["invest", "bitcoin", "stock", "crypto", "etf"]):
                result = self._qs.analyze_investment_decision(
                    amount=context.get("amount", 5000),
                    asset=context.get("asset", "investment"),
                    expected_return=context.get("expected_return", 0.15),
                    volatility=0.60 if "crypto" in q or "bitcoin" in q else 0.20,
                    num_simulations=10000,
                )
            elif any(w in q for w in ["job", "salary", "career"]):
                result = self._qs.analyze_job_change(
                    current_salary=context.get("current_salary", 80000),
                    new_salary=context.get("new_salary", 95000),
                    num_simulations=10000,
                )
            elif any(w in q for w in ["business", "startup", "venture"]):
                result = self._qs.analyze_business_venture(
                    investment=context.get("investment", 50000),
                    success_rate=context.get("success_rate", 0.40),
                    success_return=context.get("success_return", 5.0),
                    num_simulations=10000,
                )
            else:
                return f"I can analyze investment, job change, or business decisions. What type is this?"

            rec   = result.get("recommendation", "")
            stats = result.get("statistics", {})
            ev    = stats.get("mean", 0)
            sr    = stats.get("outcomes", {}).get("success_rate", 0)
            return f"{rec.strip()}\n\nExpected value: ${ev:,.0f} | Success rate: {sr:.1f}%"
        except Exception as e:
            logger.error(f"DecisionSimulator failed: {e}")
            return f"Analysis failed: {e}"

    @property
    def ready(self) -> bool:
        return self._qs is not None


# ══════════════════════════════════════════════════════════════════════════════
# MAKIMA MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class MakimaManager:
    """
    Central nervous system. All front-ends talk only to this.
    """

    def __init__(self, speak_fn: Callable = None, text_mode: bool = False):
        self._speak_fn  = speak_fn or self._default_speak
        self._text_mode = text_mode
        self._running   = False
        self._start_time = None
        self._event_hooks: Dict[str, list] = {}

        logger.info("🌸 MakimaManager initializing...")
        self._init_subsystems()
        logger.info("✅ MakimaManager ready.")

    # ── Initialization ─────────────────────────────────────────────────────────

    def _init_subsystems(self):
        # Core AI + Memory
        self._memory = _try_import("core.eternal_memory", "EternalMemory")
        self._ai     = None
        try:
            from core.ai_handler import AIHandler
            self._ai = AIHandler(memory=self._memory)
        except Exception as e:
            logger.warning(f"AIHandler failed: {e}")

        # Command Router
        self.router = None
        try:
            from core.command_router import CommandRouter
            self.router = CommandRouter(ai=self._ai, memory=self._memory)
            logger.info("🔀 CommandRouter ready")
        except Exception as e:
            logger.warning(f"CommandRouter failed: {e}")

        # Background Services
        self.services = _try_import("core.background_services", "ServiceManager", 
                                  ai=self._ai, speak_callback=self._speak_fn)
        if self.services:
            logger.info("⚙️  ServiceManager ready")

        # Preferences
        self.prefs = _try_import("core.preferences_manager", "PreferencesManager")

        # Sub-managers (pass prefs if available)
        self.music     = MusicManager(speak_fn=self._speak_fn, prefs=self.prefs)
        self.apps      = AppManager()
        self.system    = SystemManager()
        self.agents    = AgentManager(
            ai_handler=self._ai, 
            memory=self._memory,
            on_conflict=lambda item: self._fire_event("on_graph_conflict", item=item)
        )
        self.web       = WebSearchManager(ai_handler=self._ai)
        self.simulator = DecisionSimulator()

        try:
            from systems.security_manager import SecurityManager
            self.security = SecurityManager()
            logger.info("🛡️  SecurityManager ready")
        except Exception as e:
            logger.debug(f"SecurityManager unavailable: {e}")
            self.security = None

        # Tool Registry
        self.tools = None
        try:
            from makima_tools.tool_registry import ToolRegistry
            self.tools = ToolRegistry(self)
            self.tools.initialize_all()
            logger.info("🛠️  ToolRegistry ready")
        except Exception as e:
            logger.debug(f"ToolRegistry unavailable: {e}")

        # Mood Tracker
        self.mood = _try_import("systems.mood_tracker", "MoodTracker")
        if self.mood:
            logger.info("🎭 MoodTracker ready")

        # Session Summarizer
        self.summarizer = None
        try:
            from core.session_summarizer import SessionSummarizer
            self.summarizer = SessionSummarizer(ai_handler=self._ai)
            logger.info("📝 SessionSummarizer ready")
        except Exception as e:
            logger.debug(f"SessionSummarizer unavailable: {e}")

        # Daily Briefing
        self.briefing = None
        try:
            from systems.daily_briefing import DailyBriefing
            self.briefing = DailyBriefing(ai=self._ai, memory=self._memory)
            logger.info("📰 DailyBriefing ready")
        except Exception as e:
            logger.debug(f"DailyBriefing unavailable: {e}")

        # Claude Coder
        self._claude_coder = None
        try:
            from core.claude_coder import get_claude_coder
            self._claude_coder = get_claude_coder()
            if self._claude_coder.available:
                logger.info("🤖 Claude Coder ready")
        except Exception as e:
            logger.debug(f"ClaudeCoder unavailable: {e}")

        # Wire router back-references
        if self.router:
            self.router._manager = self

        # Wire proactive engine
        if self.tools and hasattr(self.tools, "_registry") and self.tools._registry:
            pe = getattr(self.tools._registry, "proactive", None)
            if pe:
                pe.speak   = self._speak_fn
                pe.execute = self.handle

    # ── Main handle() ──────────────────────────────────────────────────────────

    def handle(self, command: str, source: str = "user") -> str:
        """
        THE main entry point. Every front-end calls this.
        """
        if not command or not command.strip():
            return ""

        logger.debug(f"[{source}] handle: {command!r}")
        self._fire_event("on_command", command=command, source=source)

        if self._memory:
            self._memory.save_conversation("user", command)

        # ── Mood analysis ──
        if self.mood:
            try:
                result = self.mood.analyze(command)
                if self._ai and result.emotion not in ("neutral", ""):
                    self._ai.awareness_context["last_emotion"] = result.emotion
                if result.should_checkin:
                    self._fire_event("on_checkin", message=result.checkin_message)
            except Exception:
                pass

        # ── Daily briefing shortcut ──
        briefing_triggers = {"good morning", "morning briefing", "daily briefing",
                             "what's today look like", "full briefing", "quick briefing"}
        if any(t in command.lower() for t in briefing_triggers):
            if self.briefing:
                try:
                    style    = "quick" if "quick" in command.lower() else "full"
                    response = self.briefing.deliver(style=style)
                    return self._finish(response)
                except Exception as e:
                    logger.warning(f"Briefing error: {e}")

        # ── Tool pipeline ──
        processed = command
        if self.tools:
            try:
                result = self.tools.process_command(command)
                if isinstance(result, tuple):
                    cached, value = result
                    if cached and len(value) > 20:
                        return self._finish(value)
                    processed = value
            except Exception:
                pass

        # ── Decision simulator shortcut ──
        if self._is_decision_question(processed):
            if self.simulator.ready:
                result = self.simulator.analyze(processed)
                if result:
                    return self._finish(result)

        # ── Web search shortcut ──
        if self._needs_web_search(processed):
            if self.web.ready:
                result = self.web.search(processed)
                if result:
                    return self._finish(result)

        # ── CommandRouter ──
        if self.router:
            try:
                response, handler = self.router.route(processed)
                if response:
                    # If the AI answered but doesn't know, try the web before returning
                    if handler == "ai_chat" and self._looks_like_missing_info(response):
                        if self.web and self.web.ready:
                            web_result = self.web.search(processed)
                            if web_result:
                                return self._finish(f"I wasn't instantly sure, so I checked the web:\n\n{web_result}")
                    return self._finish(response)
            except Exception as e:
                logger.warning(f"Router failed: {e}")

        # ── V4 Agent Swarm ──
        if self.agents.ready:
            result = self.agents.run(processed)
            if result:
                return self._finish(result)

        # ── Last resort: AI ──
        fallback_reply = self._ai_direct(processed)
        if self._looks_like_missing_info(fallback_reply):
            if self.web and self.web.ready:
                web_result = self.web.search(processed)
                if web_result:
                    return self._finish(f"I didn't know off the top of my head, so I checked the web:\n\n{web_result}")
                    
        return self._finish(fallback_reply)

    def _ai_direct(self, command: str) -> str:
        if self._ai:
            try:
                ctx = self._memory.build_memory_context(command) if self._memory else ""
                reply, _ = self._ai.chat(command, context=ctx)
                return reply
            except Exception as e:
                logger.warning(f"AI direct failed: {e}")
        return "I'm having trouble thinking right now."

    def _finish(self, response: str) -> str:
        self._fire_event("on_response", response=response)
        if self._memory:
            self._memory.save_conversation("makima", response)
        return response

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self):
        self._running    = True
        self._start_time = time.time()
        self._fire_event("on_start")
        if self.services:
            self.services.start_all()
        logger.info("🌸 MakimaManager started.")

    def stop(self):
        self._running = False
        if self.services:
            self.services.stop_all()
        self._fire_event("on_stop")
        logger.info("MakimaManager stopped.")

    @property
    def running(self) -> bool:
        return self._running

    # ── Status ─────────────────────────────────────────────────────────────────

    def status(self) -> Dict:
        uptime = None
        if self._start_time:
            e = int(time.time() - self._start_time)
            uptime = f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"
        return {
            "running":   self._running,
            "uptime":    uptime,
            "timestamp": datetime.now().isoformat(),
            "subsystems": {
                "ai":        self._ai is not None,
                "memory":    self._memory is not None,
                "router":    self.router is not None,
                "music":     self.music.ready,
                "apps":      self.apps.ready,
                "system":    self.system.ready,
                "agents":    self.agents.ready,
                "web":       self.web.ready,
                "simulator": self.simulator.ready,
                "prefs":     self.prefs is not None,
                "tools":     self.tools is not None,
                "mood":      self.mood is not None,
                "briefing":  self.briefing is not None,
                "services":  self.services is not None,
            },
        }

    def status_str(self) -> str:
        s = self.status()
        active   = [k for k, v in s["subsystems"].items() if v]
        inactive = [k for k, v in s["subsystems"].items() if not v]
        lines = [f"Running for {s['uptime']}." if s["uptime"] else "Just started."]
        if active:
            lines.append(f"Active: {', '.join(active)}.")
        if inactive:
            lines.append(f"Unavailable: {', '.join(inactive)}.")
        return " ".join(lines)

    def _is_decision_question(self, text: str) -> bool:
        t = text.lower()
        if "what is" in t and "time" in t: return False
        return any(kw in t for kw in ["should i", "do i", "invest", "buy", "sell", "job", "career", "choice", "decision"])

    def _needs_web_search(self, text: str) -> bool:
        t = text.lower()
        # Personal info shouldn't trigger web search
        if any(kw in t for kw in ["my name", "my favorite", "my preference", "who am i"]):
            return False
        # Simple math shouldn't trigger web search (let AI handle it)
        import re
        if re.search(r'^what\s+is\s+[\d\s\+\-\*\/\.]+\??$', t):
            return False
        return any(kw in t for kw in ["current", "latest", "news", "price of", "weather", "search", "google", "look up"])

    def _looks_like_missing_info(self, text: str) -> bool:
        """Heuristic check to see if the AI is refusing due to lack of knowledge/internet access."""
        t = text.lower()
        refusals = [
            "i don't know", "i do not know", "i'm not sure", "i am not sure",
            "i don't have access to real-time", "i do not have access to real-time",
            "i don't have real-time", "i cannot access real-time",
            "as an ai", "as a language model", "my knowledge cutoff",
            "i cannot browse the internet", "i don't have current information",
            "i am unable to provide current", "i cannot answer that"
        ]
        return any(r in t for r in refusals)

    # ── Event System ───────────────────────────────────────────────────────────

    def on(self, event: str, callback: Callable):
        self._event_hooks.setdefault(event, []).append(callback)

    def _fire_event(self, event: str, **kwargs):
        for cb in self._event_hooks.get(event, []):
            try:
                cb(**kwargs)
            except Exception:
                pass

    def update_context(self, **kwargs):
        if self._ai:
            self._ai.awareness_context.update(kwargs)
        if self.tools and hasattr(self.tools, "_registry"):
            pe = getattr(self.tools._registry, "proactive", None)
            if pe:
                pe.update_context(**kwargs)

    # ── Configuration ──────────────────────────────────────────────────────────

    def update_credential(self, key: str, value: str) -> str:
        """Update an environment variable, save to .env, and reload subsystems."""
        import os
        os.environ[key] = value

        # Update .env file
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        key_found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)

        if not key_found:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(f"{key}={value}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        # Trigger reloads
        if key.startswith("GEMINI_") or key.startswith("OLLAMA_"):
            if self._ai:
                self._ai.reload_config()
        if key.startswith("ANTHROPIC_"):
            if self._claude_coder and hasattr(self._claude_coder, 'reload_config'):
                self._claude_coder.reload_config()
        return f"Updated {key} and saved to .env."

    # ── Convenience ───────────────────────────────────────────────────────────

    def speak(self, text: str):
        self._speak_fn(text)

    def play(self, query: str = None) -> str:
        return self.music.play(query)

    def open(self, app: str) -> str:
        return self.apps.open(app)

    def close(self, app: str) -> str:
        return self.apps.close(app)

    def search(self, query: str) -> str:
        if self.web: return self.web.search(query)
        return f"Searching for {query}."

    def search_web(self, query: str) -> str:
        """Dashboard search trigger."""
        return self.music.search_web(query)

    def screenshot(self) -> str:
        if self.system: return self.system.screenshot()
        return "Screenshot system not available."

    @staticmethod
    def _default_speak(text: str):
        print(f"[Makima] {text}")
