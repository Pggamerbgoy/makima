"""
core/tts_engine.py

TTS Engine — Tiered Voice Output
──────────────────────────────────
Priority chain (highest quality first):
  1. Edge TTS   — Microsoft Neural voices (free, online, NeerjaExpressiveNeural)
  2. pyttsx3    — SAPI5 offline fallback (always available on Windows)

Usage:
    from core.tts_engine import get_tts

    tts = get_tts()
    tts.speak("Hello!")
    tts.speak("Namaste!", lang="hi")
    tts.stop()             # interrupt mid-speech
    tts.is_busy()          # → bool

The returned object has a consistent interface regardless of which
backend is active, so the rest of V3 never needs to care which engine
is running.
"""

import os
import logging
from queue import Queue, Empty
from threading import Thread
from typing import Optional

logger = logging.getLogger("Makima.TTS")

# ── Optional backend detection ────────────────────────────────────────────────

try:
    import edge_tts
    import asyncio
    EDGE_AVAILABLE = True
except ImportError:
    EDGE_AVAILABLE = False
    logger.debug("edge-tts not installed — Edge TTS unavailable.")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.debug("pygame not installed — Edge TTS playback unavailable.")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logger.warning("pyttsx3 not installed — offline TTS unavailable.")

# Sentinel token shared across engines
_STOP = "__MAKIMA_STOP__"

# ── Neural Voice Map ──────────────────────────────────────────────────────────

VOICE_MAP = {
    "en": "en-IN-NeerjaExpressiveNeural",
    "hi": "hi-IN-SwaraNeural",
}


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Edge TTS  (Online Neural — best quality)
# ─────────────────────────────────────────────────────────────────────────────

class EdgeTTSManager:
    """
    High-quality Microsoft Neural TTS via edge-tts + pygame.
    Queue-based worker thread; supports stop-mid-speech.
    """

    def __init__(self):
        self._q: Queue = Queue()               # Text chunks queue
        self._audio_q: Queue = Queue()         # Generated MP3 paths queue
        self._busy: bool = False

        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception as e:
                logger.warning(f"pygame mixer init failed: {e}")

        self._gen_thread = Thread(target=self._generator_loop, daemon=True)
        self._gen_thread.start()
        
        self._play_thread = Thread(target=self._player_loop, daemon=True)
        self._play_thread.start()
        
        logger.info("✅ Edge TTS engine ready (pipelined stream mode).")

    # ── Workers ───────────────────────────────────────────────────────────────

    def _generator_loop(self):
        """Thread 1: Generates MP3s in the background."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        import uuid

        while True:
            item = self._q.get()
            self._busy = True

            if item == _STOP:
                self._audio_q.put(_STOP)
                continue

            text, voice, rate_str, pitch_str = self._parse_item(item)
            if not text:
                continue

            try:
                tmpId = str(uuid.uuid4())[:8]
                tmp = os.path.join(os.environ.get("TEMP", "."), f"makima_edge_{tmpId}.mp3")
                logger.debug(f"EdgeTTS generating → {text[:40]!r}")
                loop.run_until_complete(
                    self._generate(text, voice, rate_str, pitch_str, tmp)
                )
                if os.path.exists(tmp):
                    self._audio_q.put(tmp)
            except Exception as e:
                logger.warning(f"EdgeTTS generation error: {e}")

    def _player_loop(self):
        """Thread 2: Plays MP3s as soon as they are ready."""
        while True:
            item = self._audio_q.get()
            if item == _STOP:
                if PYGAME_AVAILABLE and pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                self._busy = False
                continue

            file_path = item
            if PYGAME_AVAILABLE and os.path.exists(file_path):
                try:
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.play()
                    clock = pygame.time.Clock()
                    while pygame.mixer.music.get_busy():
                        clock.tick(10)
                        if not self._audio_q.empty() and self._audio_q.queue[0] == _STOP:
                            pygame.mixer.music.stop()
                            break
                except Exception as e:
                    logger.warning(f"EdgeTTS playback error: {e}")
                finally:
                    pygame.mixer.music.unload()
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
                        
            if self._q.empty() and self._audio_q.empty():
                self._busy = False

    async def _generate(self, text: str, voice: str, rate: str, pitch: str, path: str):
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(path)

    def _parse_item(self, item) -> tuple:
        """Unpack queue item → (text, voice, rate_str, pitch_str)."""
        voice = VOICE_MAP.get("en", "en-IN-NeerjaExpressiveNeural")
        rate_str = "+0%"
        pitch_str = "+0Hz"

        if isinstance(item, tuple):
            text = str(item[0]) if item[0] else ""
            raw_rate  = item[1] if len(item) > 1 else None
            raw_pitch = item[3] if len(item) > 3 else None
            lang      = item[4] if len(item) > 4 else None

            if lang and lang in VOICE_MAP:
                voice = VOICE_MAP[lang]
            if raw_rate is not None:
                diff = int(raw_rate) - 150
                rate_str = f"{diff:+d}%"
            if raw_pitch is not None:
                pitch_str = f"{int(raw_pitch) * 2:+d}Hz"
        else:
            text = str(item)

        return text, voice, rate_str, pitch_str

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(
        self,
        text: str,
        rate: Optional[int] = None,
        volume: Optional[float] = None,
        pitch: Optional[int] = None,
        lang: Optional[str] = None,
    ):
        """Enqueue text in chunks for gapless pipelined playback."""
        if not text or not text.strip():
            return
            
        import re
        # Split by punctuation to dramatically reduce initial TTFB (Time To First Byte)
        chunks = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', text) if s.strip()]
        if not chunks:
            chunks = [text.strip()]
            
        for c in chunks:
            self._q.put((c, rate, volume, pitch, lang))

    def stop(self):
        """Interrupt current speech and flush queues."""
        try:
            while True:
                self._q.get_nowait()
        except Empty:
            pass
            
        try:
            while True:
                obsolete = self._audio_q.get_nowait()
                if isinstance(obsolete, str) and obsolete != _STOP and os.path.exists(obsolete):
                    try: os.remove(obsolete)
                    except: pass
        except Empty:
            pass
            
        self._q.put(_STOP)
        self._audio_q.put(_STOP)

    def is_busy(self) -> bool:
        return self._busy or not self._q.empty() or not self._audio_q.empty()


# ─────────────────────────────────────────────────────────────────────────────
# 2. pyttsx3  (Offline SAPI5 — always available on Windows)
# ─────────────────────────────────────────────────────────────────────────────

class Pyttsx3TTSManager:
    """
    Offline pyttsx3/SAPI5 TTS with queue-based worker thread.
    Selects a female voice automatically when available.
    """

    def __init__(self, rate: int = 165, volume: float = 0.95):
        self._rate = rate
        self._volume = volume
        self._q: Queue = Queue()
        self._busy: bool = False
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        try:
            engine = pyttsx3.init(driverName="sapi5")
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)

            voices = engine.getProperty("voices") or []
            for v in voices:
                name = v.name.lower()
                if any(kw in name for kw in ("zira", "female", "hazel", "susan", "eva")):
                    engine.setProperty("voice", v.id)
                    break

            logger.info("✅ pyttsx3 TTS engine ready (SAPI5 offline fallback).")

            while True:
                item = self._q.get()
                self._busy = True

                if item == _STOP:
                    try:
                        engine.stop()
                    except Exception:
                        pass
                    self._busy = False
                    continue

                text = item if isinstance(item, str) else item[0]
                if not text:
                    self._busy = False
                    continue

                try:
                    engine.setProperty("rate", self._rate)
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    logger.warning(f"pyttsx3 speak error: {e}")
                finally:
                    self._busy = False

        except Exception as e:
            logger.error(f"pyttsx3 engine startup failed: {e}")

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(
        self,
        text: str,
        rate: Optional[int] = None,
        volume: Optional[float] = None,
        pitch: Optional[int] = None,
        lang: Optional[str] = None,
    ):
        if not text or not text.strip():
            return
        self._q.put(str(text))

    def stop(self):
        self._q.put(_STOP)
        try:
            while True:
                self._q.get_nowait()
        except Empty:
            pass

    def is_busy(self) -> bool:
        return self._busy or not self._q.empty()


# ─────────────────────────────────────────────────────────────────────────────
# Factory — singleton per process
# ─────────────────────────────────────────────────────────────────────────────

_tts_instance = None


def get_tts():
    """
    Return the best available TTS engine as a singleton.
    Priority: Edge TTS → pyttsx3 → None (print-only).
    """
    global _tts_instance
    if _tts_instance is not None:
        return _tts_instance

    if EDGE_AVAILABLE and PYGAME_AVAILABLE:
        logger.info("TTS: Using Edge TTS (Neural, online).")
        _tts_instance = EdgeTTSManager()
    elif PYTTSX3_AVAILABLE:
        logger.info("TTS: Edge TTS unavailable — using pyttsx3 (offline).")
        _tts_instance = Pyttsx3TTSManager()
    else:
        logger.error("TTS: No engine available. Voice output disabled.")
        _tts_instance = None

    return _tts_instance
