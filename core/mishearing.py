"""
core/mishearing.py

Speech Recognition Correction Engine
──────────────────────────────────────
Fixes common speech-to-text mishearings before commands are routed.
Handles:
  • App name variants  (crow → chrome, spot a pie → spotify …)
  • YouTube phonetic noise  (you to / you do / yout → youtube)
  • Hindi command dictionary  (kholo → open, awaaz badhao → volume up …)
  • Duplicate token collapsing  (youtubeyoutube → youtube)
  • Fuzzy token matching  (thefuzz / rapidfuzz / difflib fallback)

Public API:
    from core.mishearing import correct_mishearings

    clean = correct_mishearings("hey makima kholo you to")
    # → "hey makima open youtube"
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("Makima.Mishearing")

# ── Optional fuzzy backend  (prefer thefuzz, then rapidfuzz, then difflib) ───

try:
    from thefuzz import fuzz as _fuzz          # type: ignore
except Exception:
    try:
        from rapidfuzz import fuzz as _fuzz    # type: ignore
    except Exception:
        _fuzz = None                           # difflib fallback below


# ─────────────────────────────────────────────────────────────────────────────
# Correction dictionaries
# ─────────────────────────────────────────────────────────────────────────────

# YouTube-specific phonetic variants — only applied when YouTube intent is detected
_YOUTUBE_MISHEARINGS: dict[str, str] = {
    "you to": "youtube",       "you do": "youtube",       "new home": "youtube",
    "u tube": "youtube",       "you tube": "youtube",     "tube": "youtube",
    "utube": "youtube",        "youtoob": "youtube",      "youtub": "youtube",
    "yout": "youtube",         "new tube": "youtube",     "no tube": "youtube",
    "you two": "youtube",      "you due": "youtube",      "yoo too": "youtube",
    "yoo do": "youtube",       "your to": "youtube",      "your tube": "youtube",
    "your do": "youtube",      "yer to": "youtube",       "yer tube": "youtube",
    "yer do": "youtube",       "ear to": "youtube",       "ear tube": "youtube",
    "ear do": "youtube",
    # Phrase-level
    "open your to": "open youtube",     "open your tube": "open youtube",
    "open you to": "open youtube",      "open you tube": "open youtube",
    "play your to": "play youtube",     "play your tube": "play youtube",
    # Repetition artifacts
    "youtube youtube": "youtube",       "you tube you tube": "youtube",
    "youtuyoutu": "youtube",            "youtubee": "youtube",
}

# General app name + command corrections
_MISHEARING_CORRECTIONS: dict[str, str] = {
    # ── Apps ──────────────────────────────────────────────────────────────────
    "crow": "chrome",           "crome": "chrome",          "krome": "chrome",
    "not bad": "notepad",       "note pad": "notepad",
    "spot a pie": "spotify",    "spotfy": "spotify",        "spot if eye": "spotify",
    "v s code": "vs code",      "vee es code": "vs code",
    "this p c": "this pc",      "control pannel": "control panel",
    "task manger": "task manager",
    "pint": "paint",            "sniping tool": "snipping tool",
    "download": "downloads",    "document": "documents",
    "whats app": "whatsapp",    "discorde": "discord",
    "tele gram": "telegram",    "sky pe": "skype",
    "steem": "steam",           "epik": "epic",
    "setting": "settings",      "c m d": "cmd",
    "power shell": "powershell","py charm": "pycharm",
    "wurd": "word",             "exel": "excel",
    "power point": "powerpoint","fire fox": "firefox",
    "edg": "edge",
    # ── Commands ──────────────────────────────────────────────────────────────
    "volum": "volume",          "wollume": "volume",        "bolume": "volume",
    "screen shot": "screenshot","screen chot": "screenshot",
    "remaineder": "reminder",   "remider": "reminder",      "riminder": "reminder",
    "focus mod": "focus mode",  "pocus mode": "focus mode",
    "spot a fi": "spotify",     "spot a fi eye": "spotify",
    # ── Hindi commands ────────────────────────────────────────────────────────
    "kholo": "open",            "khola": "open",            "khol do": "open",
    "band karo": "close",       "band kar do": "close",     "rok do": "stop",
    "search karo": "search",    "dhundo": "search",
    "gana bajao": "play music", "music bajao": "play music",
    "kaise ho": "how are you",  "tum kaisi ho": "how are you",
    "awaaz badhao": "volume up","awaaz badha do": "volume up",
    "awaaz tez karo": "volume up","voice badhao": "volume up",
    "awaaz zyada": "volume up",
    "awaaz kam karo": "volume down","awaaz kam": "volume down",
    "awaaz dheere": "volume down","awaaz dheere karo": "volume down",
    "voice kam karo": "volume down",
    "chup": "stop",             "chup ho jao": "stop",
    "video chalao": "play video","video rok do": "pause video",
    "poori screen": "fullscreen",
    "naya tab": "new tab",      "tab band karo": "close tab","tab band": "close tab",
    "pichla tab": "reopen tab", "reload karo": "reload page",
    "agli video": "next video", "pichli video": "previous video",
    "tez chalao": "speed up",   "dheere chalao": "slow down",
    # Wake word variants
    "hey ma kima": "hey makima","a makima": "hey makima",
}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fuzzy_ratio(a: str, b: str) -> int:
    """Return 0-100 similarity ratio between two strings."""
    if not a or not b:
        return 0
    if _fuzz is not None:
        try:
            return int(_fuzz.ratio(a, b))
        except Exception:
            pass
    from difflib import SequenceMatcher
    return int(SequenceMatcher(None, a, b).ratio() * 100)


def _fuzzy_partial_ratio(a: str, b: str) -> int:
    if not a or not b:
        return 0
    if _fuzz is not None and hasattr(_fuzz, "partial_ratio"):
        try:
            return int(_fuzz.partial_ratio(a, b))
        except Exception:
            pass
    return 100 if (a in b or b in a) else _fuzzy_ratio(a, b)


def _dedupe_adjacent_tokens(tokens: list[str]) -> list[str]:
    """Remove immediately adjacent duplicate tokens: ['a','a','b'] → ['a','b']."""
    if not tokens:
        return tokens
    out = [tokens[0]]
    for tok in tokens[1:]:
        if tok != out[-1]:
            out.append(tok)
    return out


def _collapse_repeated_substring(token: str) -> str:
    """Collapse 'abcabc' → 'abc', 'youyou' → 'you'."""
    if not token or len(token) < 4 or not token.isalpha():
        return token
    half = len(token) // 2
    for size in range(1, half + 1):
        if len(token) % size != 0:
            continue
        piece = token[:size]
        if piece * (len(token) // size) == token:
            return piece
    return token


def _clean_text(text: str) -> str:
    """Normalise whitespace and collapse repeated-substring tokens."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text.strip())
    tokens = [_collapse_repeated_substring(t) for t in text.split()]
    tokens = _dedupe_adjacent_tokens(tokens)
    return " ".join(tokens)


def _has_youtube_intent(text: str) -> bool:
    keywords = ("youtube", "open ", "play ", "search ", "video", "song", "music")
    return any(kw in text for kw in keywords)


def _normalize_youtube_token(token: str, yt_context: bool) -> str:
    """Fuzzy-map a single token to 'youtube' if it looks like it."""
    if not token or token == "youtube":
        return token
    if len(token) < 4 or not token.isalpha():
        return token
    if "youtube" in token:
        return "youtube"
    if yt_context and (token.startswith("yout") or token.endswith("tube")):
        return "youtube"
    if _fuzzy_ratio(token, "youtube") >= 92:
        return "youtube"
    if yt_context and _fuzzy_partial_ratio(token, "youtube") >= 90:
        return "youtube"
    return token


def _normalize_youtube_tokens(text: str, yt_context: bool) -> str:
    tokens = [_normalize_youtube_token(t, yt_context) for t in text.split()]
    return " ".join(tokens)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def correct_mishearings(command: str) -> str:
    """
    Apply the full correction pipeline to a raw speech-recognition string.

    Steps:
      1. Lowercase + clean duplicate tokens
      2. YouTube phrase corrections (context-gated)
      3. General app/command/Hindi dictionary corrections
      4. Fuzzy token normalisation for YouTube tokens
      5. Final cleanup pass

    Returns the corrected, lowercase command string.
    """
    if not command:
        return ""

    text = command.lower().strip()
    text = _clean_text(text)

    yt_context = _has_youtube_intent(text)

    # Step 2 — YouTube phrase fixes
    if yt_context:
        for phrase, fix in _YOUTUBE_MISHEARINGS.items():
            if phrase in text:
                text = text.replace(phrase, fix)

    # Step 3 — General dictionary
    for phrase, fix in _MISHEARING_CORRECTIONS.items():
        if phrase in text:
            text = text.replace(phrase, fix)

    # Step 4 — Fuzzy YouTube token normalisation
    text = _normalize_youtube_tokens(text, yt_context)

    # Step 5 — Final cleanup
    text = _clean_text(text)
    yt_context = yt_context or ("youtube" in text)
    text = _normalize_youtube_tokens(text, yt_context)

    logger.debug(f"Mishearing corrected: {command!r} → {text!r}")
    return text
