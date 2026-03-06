"""
tools/decision_engine.py
Decision Engine - Integrates Preferences to make smart autonomous choices for the user.

Supports multiple intent types:
  - play_music: genre/mood/artist extraction
  - open_app: app name extraction
  - web_search: query extraction
  - set_reminder: task + time extraction
  - system_control: action extraction (volume, brightness, etc.)
  - set_preference: category + value extraction

Includes LRU caching for repeated queries to reduce AI calls.
"""

import json
import logging
import time
from collections import OrderedDict
from typing import Optional, Dict, Any

logger = logging.getLogger("Makima.DecisionEngine")

# ── Cache Configuration ──────────────────────────────────────────────────────
CACHE_MAX_SIZE = 64
CACHE_TTL_SECONDS = 300  # 5 minutes


class DecisionResult:
    """Result of a preference-based decision."""

    def __init__(self, value: str, confidence: float):
        self.value = value
        self.confidence = max(0.0, min(1.0, confidence))

    def __repr__(self) -> str:
        return f"DecisionResult(value={self.value!r}, confidence={self.confidence:.2f})"

    def __bool__(self) -> bool:
        return bool(self.value) and self.confidence > 0.0


class _LRUCache:
    """Simple LRU cache with TTL for intent resolution."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl: float = CACHE_TTL_SECONDS):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, ts = self._cache[key]
            if time.monotonic() - ts < self._ttl:
                self._cache.move_to_end(key)
                self._hits += 1
                return value
            else:
                del self._cache[key]
        self._misses += 1
        return None

    def put(self, key: str, value: Any):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, time.monotonic())
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()

    @property
    def stats(self) -> Dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}


class DecisionEngine:
    """
    Smart decision engine that resolves vague commands into actionable intents.
    Uses user preferences for quick decisions and AI for complex resolution.
    """

    SYSTEM_PROMPT = """\
You are the Makima Decision Engine. Your job is to parse vague user commands into actionable JSON intents.
Return ONLY valid JSON.

Possible intents:
- "play_music": The user wants to listen to music. Extract "genre", "mood", or "artist" if provided.
- "open_app": The user wants to open an application. Extract "app" name.
- "web_search": The user wants to search for information. Extract "query".
- "set_reminder": The user wants to set a reminder. Extract "task" and "time".
- "system_control": The user wants to control system settings. Extract "action" (e.g. "volume_up", "mute", "screenshot").
- "set_preference": The user wants to set a preference. Extract "category" and "value".
- "download_files": The user wants to download a file or media. Extract "query" (what to search for), "category" (e.g., "game", "book", "image", "software"), and "file_type" (e.g., "pdf", "jpg", "exe").
- "unknown": Cannot determine an actionable command.

Example outputs:
{"intent": "play_music", "genre": "lofi", "confidence": 0.9}
{"intent": "open_app", "app": "chrome", "confidence": 0.85}
{"intent": "web_search", "query": "weather today", "confidence": 0.95}
{"intent": "set_reminder", "task": "call mom", "time": "5pm", "confidence": 0.8}
{"intent": "download_files", "query": "cyberpunk city wallpapers", "category": "image", "file_type": "png", "confidence": 0.9}
{"intent": "unknown", "confidence": 0.1}
"""

    # Context modifiers for preference-based decisions
    CONTEXT_MODIFIERS = {
        ("music", "night"): -0.1,
        ("music", "morning"): 0.05,
        ("focus", "working"): 0.1,
    }

    def __init__(self, prefs_manager, ai_handler=None):
        self.prefs = prefs_manager
        self.ai = ai_handler
        self._cache = _LRUCache()

    def decide(self, category: str, context: Optional[Dict] = None) -> DecisionResult:
        """Evaluate a category against current preferences and context to make a choice."""
        if not self.prefs:
            return DecisionResult("", 0.0)

        context = context or {}
        confidence_modifier = 0.0

        # Apply context modifiers
        time_of_day = context.get("time_of_day", "day")
        modifier_key = (category, time_of_day)
        if modifier_key in self.CONTEXT_MODIFIERS:
            confidence_modifier += self.CONTEXT_MODIFIERS[modifier_key]

        # User activity context
        if context.get("user_activity") == "focused":
            if category == "music":
                confidence_modifier += 0.05  # Slight boost for music during focus

        pref = self.prefs.get_preference(category)
        if pref:
            return DecisionResult(pref, min(1.0, max(0.0, 1.0 + confidence_modifier)))

        return DecisionResult("", 0.0)

    def handle(self, command: str) -> Optional[Dict[str, Any]]:
        """Try to resolve a vague command autonomously using the AI.
        
        Returns a dict with 'intent' key and relevant extracted fields,
        or None if resolution fails.
        """
        if not self.ai:
            return None

        # Check cache first
        cache_key = command.strip().lower()
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for: {cache_key[:40]}...")
            return cached

        try:
            response_text = self.ai.generate_response(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=command,
                temperature=0.1,
                json_mode=True
            )

            if not response_text:
                return None

            data = self._parse_json(response_text)
            if data and isinstance(data, dict):
                # Basic Sanity Checks for Local Models Hallucinations
                intent = data.get("intent")
                text_lower = command.lower()
                is_sane = True

                if intent == "play_music":
                    if not any(w in text_lower for w in ["play", "music", "song", "listen", "spotify", "track"]):
                        is_sane = False
                elif intent == "open_app":
                    if not any(w in text_lower for w in ["open", "start", "launch", "run", "app"]):
                        is_sane = False
                elif intent == "web_search":
                    # Let the AI chat handle general knowledge questions natively
                    if not any(w in text_lower for w in ["search", "google", "look up", "news", "current", "weather"]):
                        is_sane = False

                elif intent == "download_files":
                    if not any(w in text_lower for w in ["download", "get", "save", "fetch", "grab"]):
                        is_sane = False

                if not is_sane:
                    logger.debug(f"Discarding hallucinated intent: {intent} for '{command}'")
                    return None

                # Inject Preferences into Download Queries
                if intent == "download_files" and self.prefs:
                    category = data.get("category")
                    if category:
                        preferred_source = self.prefs.get_preference(category)
                        if preferred_source:
                            original_query = data.get("query", "")
                            # Append 'site:preferred.com' to the query so Scrapy hones in on it
                            injected_query = f"{original_query} site:{preferred_source}"
                            data["query"] = injected_query.strip()
                            logger.info(f"Injected preference source '{preferred_source}' into query.")

                # Cache the result
                self._cache.put(cache_key, data)
                logger.debug(f"Resolved intent: {intent} (confidence: {data.get('confidence', 'N/A')})")
                return data

        except Exception as e:
            logger.error(f"Error in DecisionEngine handler: {e}")

        return None

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Robustly parse JSON from AI response text."""
        import re

        # Try direct parse
        clean_text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON object from mixed text
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def clear_cache(self):
        """Clear the intent resolution cache."""
        self._cache.clear()
        logger.debug("Decision engine cache cleared")

    @property
    def cache_stats(self) -> Dict[str, int]:
        """Return cache hit/miss statistics."""
        return self._cache.stats
