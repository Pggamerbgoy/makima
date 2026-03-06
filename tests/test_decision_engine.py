import pytest
from tools.decision_engine import DecisionEngine, DecisionResult


class MockAIHandler:
    def generate_response(self, system_prompt, user_message, temperature=0.1, json_mode=False):
        msg = user_message.lower()
        if "music" in msg:
            return '{"intent": "play_music", "genre": "upbeat", "confidence": 0.9}'
        if "open" in msg and ("chrome" in msg or "browser" in msg):
            return '{"intent": "open_app", "app": "chrome", "confidence": 0.85}'
        if "search" in msg or "what is" in msg:
            return '{"intent": "web_search", "query": "' + user_message + '", "confidence": 0.9}'
        if "remind" in msg:
            return '{"intent": "set_reminder", "task": "call mom", "time": "5pm", "confidence": 0.8}'
        return '{"intent": "unknown", "confidence": 0.1}'


class MockPrefsManager:
    def get_preference(self, category):
        if category == "music":
            return "spotify"
        return None


# ── DecisionResult Tests ─────────────────────────────────────────────────────

def test_decision_result_repr():
    r = DecisionResult("spotify", 0.85)
    assert "spotify" in repr(r)
    assert "0.85" in repr(r)


def test_decision_result_bool():
    assert bool(DecisionResult("spotify", 0.8))
    assert not bool(DecisionResult("", 0.0))
    assert not bool(DecisionResult("", 0.5))
    assert not bool(DecisionResult("spotify", 0.0))


# ── Decide Tests ─────────────────────────────────────────────────────────────

def test_decision_engine_decide():
    prefs = MockPrefsManager()
    engine = DecisionEngine(prefs)

    # Test confidence modifier (night time drops confidence slightly to 0.9)
    res = engine.decide("music", context={"time_of_day": "night"})
    assert res.value == "spotify"
    assert res.confidence > 0.8 and res.confidence < 1.0

    # Test default confidence (day time is 1.0)
    res2 = engine.decide("music", context={"time_of_day": "day"})
    assert res2.value == "spotify"
    assert res2.confidence == 1.0

    # Test missing category
    res3 = engine.decide("anime")
    assert res3.value == ""
    assert res3.confidence == 0.0


def test_decide_no_prefs():
    engine = DecisionEngine(None)
    res = engine.decide("music")
    assert res.value == ""
    assert res.confidence == 0.0


# ── Handle Tests ─────────────────────────────────────────────────────────────

def test_handle_play_music():
    ai = MockAIHandler()
    engine = DecisionEngine(None, ai_handler=ai)

    intent = engine.handle("play some music")
    assert intent["intent"] == "play_music"
    assert intent["genre"] == "upbeat"


def test_handle_open_app():
    ai = MockAIHandler()
    engine = DecisionEngine(None, ai_handler=ai)

    intent = engine.handle("open chrome browser")
    assert intent["intent"] == "open_app"
    assert intent["app"] == "chrome"


def test_handle_web_search():
    ai = MockAIHandler()
    engine = DecisionEngine(None, ai_handler=ai)

    intent = engine.handle("search for weather today")
    assert intent["intent"] == "web_search"


def test_handle_set_reminder():
    ai = MockAIHandler()
    engine = DecisionEngine(None, ai_handler=ai)

    intent = engine.handle("remind me to call mom at 5pm")
    assert intent["intent"] == "set_reminder"
    assert intent["task"] == "call mom"


def test_handle_unknown():
    ai = MockAIHandler()
    engine = DecisionEngine(None, ai_handler=ai)

    intent = engine.handle("hello there")
    assert intent["intent"] == "unknown"


def test_handle_no_ai():
    engine = DecisionEngine(None, ai_handler=None)
    assert engine.handle("anything") is None


# ── Cache Tests ──────────────────────────────────────────────────────────────

def test_cache_hit():
    ai = MockAIHandler()
    engine = DecisionEngine(None, ai_handler=ai)

    # First call: cache miss
    result1 = engine.handle("play some music")
    stats1 = engine.cache_stats
    assert stats1["misses"] == 1

    # Second call: cache hit
    result2 = engine.handle("play some music")
    stats2 = engine.cache_stats
    assert stats2["hits"] == 1
    assert result1 == result2


def test_cache_clear():
    ai = MockAIHandler()
    engine = DecisionEngine(None, ai_handler=ai)

    engine.handle("play some music")
    assert engine.cache_stats["size"] == 1

    engine.clear_cache()
    assert engine.cache_stats["size"] == 0
