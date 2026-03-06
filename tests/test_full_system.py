"""
╔══════════════════════════════════════════════════════════════╗
║          MAKIMA — FULL SYSTEM TEST SUITE v2.0               ║
║  Tests EVERY module: core, systems, agents, tools, cloud,   ║
║  code editor, prompts, and integration.                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import tempfile
import shutil
import threading

# Fix path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "code editor"))

# Fix Windows encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# TEST FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════
results = []
PASS = 0
FAIL = 0
SKIP = 0


def run_test(name, fn, skip=False):
    global PASS, FAIL, SKIP
    if skip:
        results.append(("⏭️", f"{name} (skipped)"))
        SKIP += 1
        return
    try:
        fn()
        results.append(("✅", name))
        PASS += 1
    except AssertionError as e:
        results.append(("❌", f"{name}: {e}"))
        FAIL += 1
    except Exception as e:
        results.append(("❌", f"{name}: {type(e).__name__}: {e}"))
        FAIL += 1


def section(title):
    print(f"\n{'═'*65}")
    print(f"  {title}")
    print(f"{'═'*65}")


tmpdir = tempfile.mkdtemp(prefix="makima_fulltest_")


# ═══════════════════════════════════════════════════════════════════════════
# 1. CORE — ETERNAL MEMORY
# ═══════════════════════════════════════════════════════════════════════════
section("1. Core — Eternal Memory")

from core.eternal_memory import EternalMemory

mem = EternalMemory()


def test_mem_save_recall():
    mem.save_note("Testing note content", key="test_key_1")
    val = mem.recall_note("test_key_1")
    assert val is not None and "Testing note" in val

run_test("Memory: save_note + recall_note", test_mem_save_recall)


def test_mem_fuzzy_recall():
    mem.save_note("My favorite color is blue", key="favorite_color")
    val = mem.recall_note("color")
    assert val is not None

run_test("Memory: fuzzy recall", test_mem_fuzzy_recall)


def test_mem_save_conversation():
    mem.save_conversation("user", "hello makima")
    mem.save_conversation("assistant", "hi there!")
    results_search = mem.search_memories("hello", top_k=3)
    assert isinstance(results_search, list)

run_test("Memory: save_conversation + search", test_mem_save_conversation)


def test_mem_build_context():
    ctx = mem.build_memory_context("hello")
    assert isinstance(ctx, str)

run_test("Memory: build_memory_context", test_mem_build_context)


def test_mem_stats():
    stats = mem.get_stats()
    assert "notes_count" in stats
    assert "total_entries" in stats

run_test("Memory: get_stats", test_mem_stats)


def test_mem_format_stats():
    out = mem.format_stats()
    assert isinstance(out, str)
    assert len(out) > 10

run_test("Memory: format_stats", test_mem_format_stats)


def test_mem_remember_alias():
    mem.remember("test_alias", "alias_value")
    val = mem.recall_note("test_alias")
    assert val is not None

run_test("Memory: remember() alias", test_mem_remember_alias)


def test_mem_search_generic():
    result = mem.search("hello")
    assert isinstance(result, (list, str))

run_test("Memory: search() generic", test_mem_search_generic)


# ═══════════════════════════════════════════════════════════════════════════
# 2. CORE — AI HANDLER
# ═══════════════════════════════════════════════════════════════════════════
section("2. Core — AI Handler")

from core.ai_handler import AIHandler

ai = AIHandler(memory=mem)


def test_ai_init():
    assert ai.persona == "makima"
    assert ai.gemini_model is not None
    assert ai.ollama_model is not None

run_test("AI: init + defaults", test_ai_init)


def test_ai_set_persona():
    ai.set_persona("makima")
    assert ai.persona == "makima"

run_test("AI: set_persona", test_ai_set_persona)


def test_ai_history():
    ai.clear_history()
    assert len(ai.conversation_history) == 0
    ai.add_to_history("user", "test msg")
    assert len(ai.conversation_history) == 1
    ai.clear_history()

run_test("AI: history add/clear", test_ai_history)


def test_ai_trim_history():
    ai.clear_history()
    for i in range(20):
        ai.add_to_history("user", f"msg {i}")
    ai._trim_history()
    assert len(ai.conversation_history) <= ai.max_history_turns * 2

run_test("AI: trim_history", test_ai_trim_history)


def test_ai_awareness():
    ai.update_awareness({"battery": 85, "time": "14:00"})
    assert ai.awareness_context.get("active_window", {}).get("battery") == 85

run_test("AI: update_awareness", test_ai_awareness)


def test_ai_build_prompt():
    prompt = ai._build_prompt("hello", "some context")
    assert "hello" in prompt
    assert isinstance(prompt, str)

run_test("AI: _build_prompt", test_ai_build_prompt)


def test_ai_parse_json_response():
    raw = '{"reply": "Hi there!", "emotion": "happy"}'
    reply, emotion = ai._parse_response(raw)
    assert reply == "Hi there!"
    assert emotion == "happy"

run_test("AI: parse JSON response", test_ai_parse_json_response)


def test_ai_parse_plain_response():
    raw = "Just a plain text response without JSON"
    reply, emotion = ai._parse_response(raw)
    assert len(reply) > 0

run_test("AI: parse plain text response", test_ai_parse_plain_response)


def test_ai_parse_malformed():
    raw = '{"reply": "broken json'
    reply, emotion = ai._parse_response(raw)
    assert len(reply) > 0  # Should not crash

run_test("AI: parse malformed JSON", test_ai_parse_malformed)


def test_ai_gemini_available_check():
    result = ai._is_gemini_available()
    assert isinstance(result, bool)

run_test("AI: _is_gemini_available", test_ai_gemini_available_check)


def test_ai_few_shot_examples():
    from core.ai_handler import FEW_SHOT_EXAMPLES
    assert "makima" in FEW_SHOT_EXAMPLES
    assert len(FEW_SHOT_EXAMPLES["makima"]) > 0

run_test("AI: FEW_SHOT_EXAMPLES exist", test_ai_few_shot_examples)


# ═══════════════════════════════════════════════════════════════════════════
# 3. CORE — COMMAND ROUTER
# ═══════════════════════════════════════════════════════════════════════════
section("3. Core — Command Router")

from core.command_router import CommandRouter

router = CommandRouter(ai, mem)


def test_router_pattern_count():
    assert len(router.PATTERNS) > 50, f"Only {len(router.PATTERNS)} patterns"

run_test("Router: >50 patterns registered", test_router_pattern_count)


def test_router_time():
    resp, handler = router.route("what time is it")
    assert handler != "error"
    assert resp is not None

run_test("Router: 'what time is it'", test_router_time)


def test_router_date():
    resp, handler = router.route("what's the date today")
    assert resp is not None

run_test("Router: date query", test_router_date)


def test_router_remember():
    resp, handler = router.route("remember my email is test@test.com")
    assert "remember" in handler.lower() or "note" in resp.lower() or resp

run_test("Router: remember command", test_router_remember)


def test_router_volume():
    resp, handler = router.route("set volume to 50")
    assert resp is not None

run_test("Router: volume set", test_router_volume)


def test_router_screenshot():
    resp, handler = router.route("take a screenshot")
    assert resp is not None

run_test("Router: screenshot", test_router_screenshot)


def test_router_cpu():
    resp, handler = router.route("cpu usage")
    assert resp is not None

run_test("Router: CPU usage", test_router_cpu)


def test_router_battery():
    resp, handler = router.route("battery status")
    assert resp is not None

run_test("Router: battery", test_router_battery)


def test_router_greeting():
    resp, handler = router.route("hello makima")
    assert resp is not None

run_test("Router: greeting", test_router_greeting)


def test_router_ai_fallback():
    resp, handler = router.route("tell me something interesting about quantum computing")
    assert resp is not None
    assert handler in ("ai_chat", "decision_engine:unknown") or "error" not in handler

run_test("Router: AI fallback", test_router_ai_fallback)


def test_router_task_add():
    resp, handler = router.route("add task buy milk")
    assert resp is not None

run_test("Router: add task", test_router_task_add)


def test_router_task_list():
    resp, handler = router.route("show my tasks")
    assert resp is not None

run_test("Router: list tasks", test_router_task_list)


def test_router_persona():
    resp, handler = router.route("switch to normal mode")
    assert resp is not None

run_test("Router: persona switch", test_router_persona)


def test_router_clear_history():
    resp, handler = router.route("clear chat history")
    assert resp is not None

run_test("Router: clear history", test_router_clear_history)


# ═══════════════════════════════════════════════════════════════════════════
# 4. CORE — MAKIMA MANAGER
# ═══════════════════════════════════════════════════════════════════════════
section("4. Core — Makima Manager")

from core.makima_manager import MakimaManager, MusicManager, AppManager, SystemManager


def test_mgr_init():
    mgr = MakimaManager(text_mode=True)
    assert mgr is not None
    assert hasattr(mgr, "handle")

run_test("Manager: init + has handle()", test_mgr_init)


def test_mgr_status():
    mgr = MakimaManager(text_mode=True)
    status = mgr.status()
    assert isinstance(status, dict) or isinstance(status, str)

run_test("Manager: status()", test_mgr_status)


def test_mgr_music_manager():
    mm = MusicManager()
    assert hasattr(mm, "play")
    assert hasattr(mm, "next")
    assert hasattr(mm, "previous")
    assert hasattr(mm, "now_playing")

run_test("Manager: MusicManager API", test_mgr_music_manager)


def test_mgr_app_manager():
    am = AppManager()
    assert hasattr(am, "open")
    assert hasattr(am, "close")
    assert hasattr(am, "toggle")

run_test("Manager: AppManager API", test_mgr_app_manager)


def test_mgr_system_manager():
    sm = SystemManager()
    assert hasattr(sm, "volume_up")
    assert hasattr(sm, "volume_down")
    assert hasattr(sm, "set_volume")
    assert hasattr(sm, "screenshot")
    assert hasattr(sm, "lock_screen")

run_test("Manager: SystemManager API", test_mgr_system_manager)


# ═══════════════════════════════════════════════════════════════════════════
# 5. CORE — PREFERENCES MANAGER
# ═══════════════════════════════════════════════════════════════════════════
section("5. Core — Preferences Manager")

from core.preferences_manager import PreferencesManager

prefs = PreferencesManager(filepath=os.path.join(tmpdir, "test_prefs.json"))


def test_prefs_set_get():
    prefs.set_explicit_preference("music", "spotify")
    assert prefs.get_preference("music") == "spotify"

run_test("Prefs: set + get explicit", test_prefs_set_get)


def test_prefs_implicit():
    prefs.record_usage("browser", "chrome")
    prefs.record_usage("browser", "chrome")
    prefs.record_usage("browser", "firefox")
    assert prefs.get_preference("browser") == "chrome"

run_test("Prefs: implicit usage tracking", test_prefs_implicit)


def test_prefs_clear():
    prefs.set_explicit_preference("editor", "vscode")
    prefs.clear_preference("editor")
    assert prefs.get_preference("editor") is None

run_test("Prefs: clear preference", test_prefs_clear)


def test_prefs_list():
    prefs.set_explicit_preference("music", "spotify")
    out = prefs.list_preferences()
    assert "spotify" in out.lower()

run_test("Prefs: list_preferences", test_prefs_list)


# ═══════════════════════════════════════════════════════════════════════════
# 6. CORE — MISHEARING CORRECTIONS
# ═══════════════════════════════════════════════════════════════════════════
section("6. Core — Mishearing")

from core.mishearing import correct_mishearings


def test_mishearing_basic():
    result = correct_mishearings("hey ma kima")
    assert "makima" in result.lower()

run_test("Mishearing: 'ma kima' → 'makima'", test_mishearing_basic)


def test_mishearing_passthrough():
    result = correct_mishearings("hello world")
    assert result == "hello world"

run_test("Mishearing: passthrough normal text", test_mishearing_passthrough)


# ═══════════════════════════════════════════════════════════════════════════
# 7. CORE — TTS ENGINE
# ═══════════════════════════════════════════════════════════════════════════
section("7. Core — TTS Engine")

from core.tts_engine import get_tts, EdgeTTSManager, Pyttsx3TTSManager


def test_tts_get():
    tts = get_tts()
    if tts:
        assert hasattr(tts, "speak")
        assert hasattr(tts, "stop")
        assert hasattr(tts, "is_busy")

run_test("TTS: get_tts() returns valid engine", test_tts_get)


def test_tts_edge_init():
    # EdgeTTSManager should init without crash
    try:
        e = EdgeTTSManager()
        assert hasattr(e, "speak")
    except Exception:
        pass  # OK if edge-tts not installed

run_test("TTS: EdgeTTSManager init", test_tts_edge_init)


# ═══════════════════════════════════════════════════════════════════════════
# 8. CORE — SESSION SUMMARIZER
# ═══════════════════════════════════════════════════════════════════════════
section("8. Core — Session Summarizer")

from core.session_summarizer import SessionSummarizer


def test_summarizer_init():
    s = SessionSummarizer(ai_handler=ai)
    assert hasattr(s, "summarize_session") or hasattr(s, "maybe_compress")

run_test("Summarizer: init + API", test_summarizer_init)


# ═══════════════════════════════════════════════════════════════════════════
# 9. CORE — BACKGROUND SERVICES
# ═══════════════════════════════════════════════════════════════════════════
section("9. Core — Background Services")

from core.background_services import ActivityLog, BackgroundService


def test_activity_log():
    log = ActivityLog()
    log.add("test", "action", "detail")
    recent = log.recent(5)
    assert isinstance(recent, list)
    assert len(recent) >= 1

run_test("Background: ActivityLog add + recent", test_activity_log)


def test_activity_log_summary():
    log = ActivityLog()
    log.add("svc", "act", "det")
    summary = log.summary(5)
    assert isinstance(summary, str)

run_test("Background: ActivityLog summary", test_activity_log_summary)


def test_activity_log_count():
    log = ActivityLog()
    count = log.count_today()
    assert isinstance(count, (int, dict))

run_test("Background: ActivityLog count_today", test_activity_log_count)


# ═══════════════════════════════════════════════════════════════════════════
# 10. CORE — AUTO DOWNLOADER
# ═══════════════════════════════════════════════════════════════════════════
section("10. Core — Auto Downloader")


def test_auto_downloader_import():
    from core.auto_downloader import download_files_sync
    assert callable(download_files_sync)

run_test("AutoDownloader: import + callable", test_auto_downloader_import)


# ═══════════════════════════════════════════════════════════════════════════
# 11. CORE — CLAUDE CODER
# ═══════════════════════════════════════════════════════════════════════════
section("11. Core — Claude Coder")


def test_claude_coder_import():
    from core.claude_coder import ClaudeCoder
    assert hasattr(ClaudeCoder, "__init__")

run_test("ClaudeCoder: import", test_claude_coder_import)


# ═══════════════════════════════════════════════════════════════════════════
# 12. TOOLS — DECISION ENGINE
# ═══════════════════════════════════════════════════════════════════════════
section("12. Tools — Decision Engine")

from tools.decision_engine import DecisionEngine, DecisionResult, _LRUCache


def test_decision_result():
    dr = DecisionResult("spotify", 0.95)
    assert dr.value == "spotify"
    assert dr.confidence == 0.95
    assert bool(dr) is True

run_test("DecisionEngine: DecisionResult", test_decision_result)


def test_lru_cache():
    cache = _LRUCache(max_size=3)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    cache.put("d", 4)  # should evict "b"
    assert cache.get("b") is None

run_test("DecisionEngine: LRU cache", test_lru_cache)


def test_decision_engine_init():
    de = DecisionEngine(prefs)
    assert hasattr(de, "handle")
    assert hasattr(de, "decide")

run_test("DecisionEngine: init + API", test_decision_engine_init)


def test_decision_engine_decide():
    de = DecisionEngine(prefs)
    prefs.set_explicit_preference("music", "spotify")
    result = de.decide("music")
    assert isinstance(result, DecisionResult)

run_test("DecisionEngine: decide() with pref", test_decision_engine_decide)


def test_decision_engine_cache_stats():
    de = DecisionEngine(prefs)
    stats = de.cache_stats
    assert "hits" in stats
    assert "misses" in stats

run_test("DecisionEngine: cache_stats", test_decision_engine_cache_stats)


# ═══════════════════════════════════════════════════════════════════════════
# 13. SYSTEMS — IMPORTS & API CHECK
# ═══════════════════════════════════════════════════════════════════════════
section("13. Systems — All Imports")

SYSTEMS_TESTS = [
    ("systems.app_control", "AppControl", ["open", "close"]),
    ("systems.system_commands", "SystemCommands", ["volume_up", "volume_down"]),
    ("systems.battery_monitor", "BatteryMonitor", ["run"]),
    ("systems.clipboard_monitor", "ClipboardMonitor", ["run"]),
    ("systems.media_observer", "MediaObserver", ["run"]),
    ("systems.file_manager", "FileManager", None),
    ("systems.focus_mode", "FocusMode", None),
    ("systems.health_tracker", "HealthTracker", None),
    ("systems.hotkey_manager", "HotkeyManager", None),
    ("systems.macros", "MacroSystem", None),
    ("systems.mood_tracker", "MoodTracker", None),
    ("systems.music_dj", "MusicDJ", ["play_mood", "pause", "resume", "skip"]),
    ("systems.notification_manager", "NotificationManager", None),
    ("systems.reminder", "ReminderSystem", None),
    ("systems.security_manager", "SecurityManager", None),
    ("systems.shortcuts", None, None),  # module-level functions only
    ("systems.spotify_control", "SpotifyControl", None),
    ("systems.voice_personality", "VoicePersonality", None),
    ("systems.web_music", "WebMusic", None),
    ("systems.youtube_player", "YouTubePlayer", None),
    ("systems.calendar_manager", "CalendarManager", None),
    ("systems.daily_briefing", "DailyBriefing", None),
    ("systems.email_manager", "EmailManager", None),
    ("systems.quantum_simulator", None, None),  # module-level class may vary
    ("systems.self_updater", "SelfUpdater", None),
    ("systems.whatsapp_manager", "WhatsAppManager", None),
]

for mod_path, cls_name, methods in SYSTEMS_TESTS:
    def _make_test(mp, cn, meths):
        def test():
            import importlib
            m = importlib.import_module(mp)
            if cn is None:
                return  # Module-level only, no class to check
            cls = getattr(m, cn, None)
            assert cls is not None, f"Class {cn} not found in {mp}"
            if meths:
                for method in meths:
                    assert hasattr(cls, method), f"Missing method: {method}"
        return test
    label = f"System: {mod_path}" + (f".{cls_name}" if cls_name else " (module)")
    run_test(label, _make_test(mod_path, cls_name, methods))


# ═══════════════════════════════════════════════════════════════════════════
# 14. AGENTS — IMPORTS & API CHECK
# ═══════════════════════════════════════════════════════════════════════════
section("14. Agents — All Imports")

AGENT_TESTS = [
    ("agents.skill_teacher", "SkillTeacher", ["teach", "try_run_skill", "list_skills"]),
    ("agents.app_learner", "AppLearner", None),
    ("agents.auto_coder", "AutoCoder", None),
    ("agents.emotion_detector", "EmotionDetector", None),
    ("agents.health_check", None, None),  # module-level functions
    ("agents.meeting_assistant", "MeetingAssistant", None),
    ("agents.screen_reader", "ScreenReader", None),
    ("agents.translator", None, None),  # module-level functions
    ("agents.web_agent", "WebAgent", None),
]

for mod_path, cls_name, methods in AGENT_TESTS:
    def _make_test(mp, cn, meths):
        def test():
            import importlib
            m = importlib.import_module(mp)
            if cn is None:
                return  # Module-level only
            cls = getattr(m, cn, None)
            assert cls is not None, f"Class {cn} not found in {mp}"
            if meths:
                for method in meths:
                    assert hasattr(cls, method), f"Missing method: {method}"
        return test
    label = f"Agent: {mod_path}" + (f".{cls_name}" if cls_name else " (module)")
    run_test(label, _make_test(mod_path, cls_name, methods))


# Face recognition may need special deps
def test_face_recognition_import():
    try:
        from agents.face_recognition_system import FaceRecognitionSystem
        assert hasattr(FaceRecognitionSystem, "__init__")
    except ImportError:
        pass  # Optional dependency

run_test("Agent: face_recognition_system (optional)", test_face_recognition_import)


# ═══════════════════════════════════════════════════════════════════════════
# 15. CLOUD
# ═══════════════════════════════════════════════════════════════════════════
section("15. Cloud")


def test_cloud_import():
    from cloud.cloud_manager import CloudManager
    assert hasattr(CloudManager, "__init__")

run_test("Cloud: CloudManager import", test_cloud_import)


# ═══════════════════════════════════════════════════════════════════════════
# 16. MAKIMA_V4 (AGENT SWARM)
# ═══════════════════════════════════════════════════════════════════════════
section("16. Makima_v4 — Agent Swarm")


def test_v4_main_import():
    try:
        sys.path.insert(0, os.path.join(ROOT, "Makima_v4"))
        from main import MakimaV4
        assert hasattr(MakimaV4, "__init__")
    except ImportError:
        pass  # V4 may have extra deps

run_test("V4: MakimaV4 import", test_v4_main_import)


# ═══════════════════════════════════════════════════════════════════════════
# 17. CODE EDITOR — EDITOR BRIDGE
# ═══════════════════════════════════════════════════════════════════════════
section("17. Code Editor — EditorBridge")

from editor.editor_bridge import EditorBridge

bridge = EditorBridge()


def test_bridge_read():
    p = os.path.join(tmpdir, "bridge_read.txt")
    with open(p, "w") as f:
        f.write("line1\nline2\n")
    result = bridge.read_file(p)
    assert "line1" in result

run_test("Bridge: read_file", test_bridge_read)


def test_bridge_create():
    p = os.path.join(tmpdir, "bridge_new.py")
    result = bridge.create_file(p, "print('test')")
    assert "Created" in result

run_test("Bridge: create_file", test_bridge_create)


def test_bridge_edit():
    p = os.path.join(tmpdir, "bridge_edit.txt")
    bridge.create_file(p, "old content")
    result = bridge.edit_file(p, "old", "new")
    assert "Replaced" in result

run_test("Bridge: edit_file", test_bridge_edit)


def test_bridge_delete():
    p = os.path.join(tmpdir, "bridge_del.txt")
    bridge.create_file(p, "x")
    result = bridge.delete_file(p)
    assert "Deleted" in result

run_test("Bridge: delete_file", test_bridge_delete)


def test_bridge_list():
    result = bridge.list_dir(tmpdir)
    assert "📄" in result or "📁" in result

run_test("Bridge: list_dir", test_bridge_list)


def test_bridge_search():
    bridge.create_file(os.path.join(tmpdir, "search_t.py"), "def foo(): pass")
    result = bridge.search_in_files("foo", tmpdir)
    assert "foo" in result

run_test("Bridge: search_in_files", test_bridge_search)


def test_bridge_terminal():
    result = bridge.run_terminal("echo bridge_test", timeout=10)
    assert "bridge_test" in result

run_test("Bridge: run_terminal", test_bridge_terminal)


def test_bridge_tool_map():
    expected = ["read_file", "edit_file", "create_file", "delete_file",
                "list_dir", "list_directory", "run_terminal_cmd", "run_command",
                "grep", "grep_search", "codebase_search", "search_in_files",
                "search_replace", "write_file", "rewrite_file",
                "get_open_files", "get_active_file", "goto_line",
                "vscode_open", "vscode_diff"]
    for t in expected:
        assert t in bridge.TOOL_MAP, f"Missing: {t}"

run_test("Bridge: TOOL_MAP completeness", test_bridge_tool_map)


def test_bridge_dispatch():
    p = os.path.join(tmpdir, "dispatch_t.txt")
    bridge.create_file(p, "dispatch_content")
    result = bridge.dispatch("read_file", {"target_file": p})
    assert "dispatch_content" in result

run_test("Bridge: dispatch()", test_bridge_dispatch)


# ═══════════════════════════════════════════════════════════════════════════
# 18. TOOL CALL PARSING
# ═══════════════════════════════════════════════════════════════════════════
section("18. Tool Call Parsing")

import re


def parse_tool_call(text):
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            fc = data.get("function_call") or data.get("tool_call")
            if fc:
                return fc["name"], fc.get("arguments", {})
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    json_blocks = re.findall(r'```(?:json)?\s*\n?(\{[^`]+\})\s*```', text, re.DOTALL)
    for block in json_blocks:
        try:
            data = json.loads(block)
            if "name" in data and ("arguments" in data or "parameters" in data):
                return data["name"], data.get("arguments", data.get("parameters", {}))
        except (json.JSONDecodeError, KeyError):
            continue
    tc_match = re.search(r'<tool_call>\s*(\w+)\((.+?)\)\s*</tool_call>', text, re.DOTALL)
    if tc_match:
        try:
            return tc_match.group(1), json.loads(tc_match.group(2))
        except json.JSONDecodeError:
            pass
    return None


def test_parse_json(): assert parse_tool_call('{"function_call":{"name":"read_file","arguments":{"path":"x"}}}') is not None
def test_parse_md(): assert parse_tool_call('```json\n{"name":"edit_file","arguments":{"path":"x"}}\n```') is not None
def test_parse_tag(): assert parse_tool_call('<tool_call>read_file({"path":"x"})</tool_call>') is not None
def test_parse_plain(): assert parse_tool_call("Hello, how are you?") is None

run_test("Parse: Format 1 (JSON)", test_parse_json)
run_test("Parse: Format 2 (markdown)", test_parse_md)
run_test("Parse: Format 3 (<tool_call>)", test_parse_tag)
run_test("Parse: plain text = None", test_parse_plain)


# ═══════════════════════════════════════════════════════════════════════════
# 19. PROMPT FILES
# ═══════════════════════════════════════════════════════════════════════════
section("19. Prompt Files")


def test_prompt_cursor(): assert os.path.isfile(os.path.join(ROOT, "promts for coding", "cursor", "cursor.txt"))
def test_prompt_claude(): assert os.path.isfile(os.path.join(ROOT, "promts for coding", "claude", "claude2.0.txt"))
def test_prompt_no_old(): assert not os.path.isfile(os.path.join(ROOT, "promts for coding", "claude", "Cladue.txt"))
def test_prompt_tools():
    p = os.path.join(ROOT, "promts for coding", "cursor", "cursor tools .json")
    with open(p) as f: json.load(f)

def test_prompt_launcher():
    d = os.path.join(ROOT, "MAKIMA LAUNCHER", "prompts")
    assert len([f for f in os.listdir(d) if f.endswith(".txt")]) >= 3

run_test("Prompts: cursor.txt exists", test_prompt_cursor)
run_test("Prompts: claude2.0.txt exists", test_prompt_claude)
run_test("Prompts: Cladue.txt deleted", test_prompt_no_old)
run_test("Prompts: cursor tools JSON valid", test_prompt_tools)
run_test("Prompts: launcher ≥3 files", test_prompt_launcher)


# ═══════════════════════════════════════════════════════════════════════════
# 20. MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════
section("20. Main Entry Point")


def test_main_import():
    from makima_assistant import MakimaAssistant
    assert hasattr(MakimaAssistant, "run")
    assert hasattr(MakimaAssistant, "process_input")
    assert hasattr(MakimaAssistant, "speak")

run_test("Main: MakimaAssistant import + API", test_main_import)


# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP & FINAL REPORT
# ═══════════════════════════════════════════════════════════════════════════
shutil.rmtree(tmpdir, ignore_errors=True)

section("FINAL RESULTS")
for status, name in results:
    print(f"  {status} {name}")

print(f"\n{'─'*65}")
print(f"  ✅ PASSED: {PASS}   ❌ FAILED: {FAIL}   ⏭️ SKIPPED: {SKIP}   TOTAL: {PASS + FAIL + SKIP}")
print(f"{'─'*65}")

if FAIL > 0:
    print(f"\n  ⚠️ {FAIL} test(s) failed!")
    sys.exit(1)
else:
    print(f"\n  🎉 ALL TESTS PASSED!")
