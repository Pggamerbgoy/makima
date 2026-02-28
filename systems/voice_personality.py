"""
systems/voice_personality.py

Voice Personality System
─────────────────────────
Customize Makima's voice completely:
  - Voice selection (female/male, different engines)
  - Speed (slow/normal/fast)
  - Pitch adjustment
  - Accent/language preference
  - Emotion-based voice modulation (sounds sadder, more excited, etc.)
  - ElevenLabs integration for ultra-realistic voice (optional)
  - Offline fallback via pyttsx3 with full control

Commands:
  "Change voice to [name]"
  "Speak faster / slower"
  "Set voice speed to [number]"
  "Make your voice higher / lower"
  "List available voices"
  "Use ElevenLabs voice"
  "Reset voice to default"
"""

import os
import io
import json
import logging
import platform
import threading
from typing import Optional, Callable

logger = logging.getLogger("Makima.VoicePersonality")
OS = platform.system()

VOICE_CONFIG_FILE = "voice_config.json"

# ElevenLabs voice presets
ELEVENLABS_VOICES = {
    "makima":    "21m00Tcm4TlvDq8ikWAM",  # Rachel — calm, clear
    "warm":      "AZnzlk1XvdvUeBnXmlld",  # Domi — warm
    "soft":      "EXAVITQu4vr4xnSDxMaL",  # Bella — soft
    "powerful":  "ErXwobaYiN019PkySvjV",  # Antoni — powerful
    "friendly":  "MF3mGyEYCl7XYWbV9V6O",  # Elli — friendly
}

DEFAULT_CONFIG = {
    "engine": "pyttsx3",          # "pyttsx3" | "elevenlabs" | "gtts"
    "voice_name": "auto",         # auto = best available female
    "speed": 165,                 # words per minute (pyttsx3)
    "pitch": 1.0,                 # 0.5–2.0 relative pitch
    "volume": 1.0,                # 0.0–1.0
    "elevenlabs_voice": "makima",
    "elevenlabs_stability": 0.75,
    "elevenlabs_similarity": 0.85,
    "emotion_modulation": True,   # adjust voice based on detected emotion
}

# Emotion → voice adjustments
EMOTION_VOICE_MAP = {
    "happy":   {"speed_mult": 1.1, "pitch_mult": 1.05},
    "excited": {"speed_mult": 1.2, "pitch_mult": 1.1},
    "sad":     {"speed_mult": 0.85, "pitch_mult": 0.95},
    "stressed":{"speed_mult": 0.9, "pitch_mult": 1.0},
    "calm":    {"speed_mult": 0.95, "pitch_mult": 1.0},
    "tired":   {"speed_mult": 0.85, "pitch_mult": 0.9},
    "angry":   {"speed_mult": 0.95, "pitch_mult": 0.95},
    "neutral": {"speed_mult": 1.0, "pitch_mult": 1.0},
}


class VoicePersonality:
    """Manages all aspects of Makima's voice output."""

    def __init__(self):
        self.config = self._load_config()
        self._tts_engine = None
        self._engine_lock = threading.Lock()
        self._current_emotion = "neutral"
        self._init_engine()

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        if os.path.exists(VOICE_CONFIG_FILE):
            try:
                with open(VOICE_CONFIG_FILE) as f:
                    cfg = json.load(f)
                    return {**DEFAULT_CONFIG, **cfg}
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def _save_config(self):
        with open(VOICE_CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    # ── Engine Init ───────────────────────────────────────────────────────────

    def _init_engine(self):
        engine = self.config.get("engine", "pyttsx3")
        if engine == "pyttsx3":
            self._init_pyttsx3()
        elif engine == "elevenlabs":
            self._init_elevenlabs()
        elif engine == "gtts":
            pass  # Initialized per-call

    def _init_pyttsx3(self):
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._apply_pyttsx3_settings()
            logger.info("✅ pyttsx3 voice engine ready.")
        except Exception as e:
            logger.warning(f"pyttsx3 init failed: {e}")

    def _apply_pyttsx3_settings(self):
        if not self._tts_engine:
            return
        try:
            self._tts_engine.setProperty("rate", int(self.config["speed"]))
            self._tts_engine.setProperty("volume", self.config["volume"])

            # Voice selection
            voices = self._tts_engine.getProperty("voices")
            target = self.config.get("voice_name", "auto").lower()

            selected = None
            if target == "auto":
                # Prefer female voice
                for v in voices:
                    name = v.name.lower()
                    if any(kw in name for kw in ["zira", "female", "hazel", "susan", "eva"]):
                        selected = v
                        break
            else:
                for v in voices:
                    if target in v.name.lower():
                        selected = v
                        break

            if selected:
                self._tts_engine.setProperty("voice", selected.id)
                logger.info(f"Voice set to: {selected.name}")
        except Exception as e:
            logger.warning(f"Voice settings error: {e}")

    def _init_elevenlabs(self):
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            logger.warning("ELEVENLABS_API_KEY not set. Falling back to pyttsx3.")
            self.config["engine"] = "pyttsx3"
            self._init_pyttsx3()
        else:
            logger.info("✅ ElevenLabs voice engine configured.")

    # ── Speaking ──────────────────────────────────────────────────────────────

    def speak(self, text: str, emotion: str = None):
        """Speak text using configured engine with optional emotion modulation."""
        if not text:
            return

        active_emotion = emotion or self._current_emotion
        engine = self.config.get("engine", "pyttsx3")

        if engine == "elevenlabs":
            self._speak_elevenlabs(text, active_emotion)
        elif engine == "gtts":
            self._speak_gtts(text)
        else:
            self._speak_pyttsx3(text, active_emotion)

    def _speak_pyttsx3(self, text: str, emotion: str = "neutral"):
        if not self._tts_engine:
            print(f"Makima: {text}")
            return

        with self._engine_lock:
            try:
                # Emotion-based speed/pitch modulation
                if self.config.get("emotion_modulation", True):
                    mod = EMOTION_VOICE_MAP.get(emotion, EMOTION_VOICE_MAP["neutral"])
                    base_speed = self.config["speed"]
                    adjusted_speed = int(base_speed * mod["speed_mult"])
                    self._tts_engine.setProperty("rate", adjusted_speed)

                self._tts_engine.say(text)
                self._tts_engine.runAndWait()

                # Reset to base speed after
                self._tts_engine.setProperty("rate", self.config["speed"])
            except Exception as e:
                logger.warning(f"pyttsx3 speak error: {e}")
                print(f"Makima: {text}")

    def _speak_elevenlabs(self, text: str, emotion: str = "neutral"):
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        voice_id = ELEVENLABS_VOICES.get(
            self.config.get("elevenlabs_voice", "makima"),
            ELEVENLABS_VOICES["makima"]
        )
        try:
            import requests
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "Accept": "audio/mpeg",
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": self.config.get("elevenlabs_stability", 0.75),
                        "similarity_boost": self.config.get("elevenlabs_similarity", 0.85),
                    },
                },
                timeout=10,
            )
            if response.status_code == 200:
                self._play_audio_bytes(response.content)
            else:
                logger.warning(f"ElevenLabs error: {response.status_code}")
                self._speak_pyttsx3(text, emotion)
        except Exception as e:
            logger.warning(f"ElevenLabs speak error: {e}")
            self._speak_pyttsx3(text, emotion)

    def _speak_gtts(self, text: str):
        try:
            from gtts import gTTS
            import tempfile, os
            tts = gTTS(text=text, lang="en", slow=False)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                path = f.name
            tts.save(path)
            self._play_audio_file(path)
            os.unlink(path)
        except Exception as e:
            logger.warning(f"gTTS error: {e}")
            self._speak_pyttsx3(text)

    def _play_audio_bytes(self, audio_bytes: bytes):
        try:
            import pygame
            pygame.mixer.init()
            sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))
            sound.play()
            while pygame.mixer.get_busy():
                import time; time.sleep(0.05)
        except ImportError:
            import tempfile, subprocess
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                path = f.name
            self._play_audio_file(path)
            os.unlink(path)

    def _play_audio_file(self, path: str):
        import subprocess, platform
        OS = platform.system()
        try:
            if OS == "Windows":
                subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"])
            elif OS == "Linux":
                subprocess.run(["aplay", path], capture_output=True)
            elif OS == "Darwin":
                subprocess.run(["afplay", path])
        except Exception as e:
            logger.warning(f"Audio playback error: {e}")

    # ── Controls ──────────────────────────────────────────────────────────────

    def set_speed(self, wpm: int) -> str:
        wpm = max(80, min(350, wpm))
        self.config["speed"] = wpm
        if self._tts_engine:
            self._tts_engine.setProperty("rate", wpm)
        self._save_config()
        label = "slow" if wpm < 130 else "fast" if wpm > 200 else "normal"
        return f"Voice speed set to {wpm} WPM ({label})."

    def faster(self) -> str:
        return self.set_speed(self.config["speed"] + 20)

    def slower(self) -> str:
        return self.set_speed(self.config["speed"] - 20)

    def set_volume(self, level: float) -> str:
        level = max(0.0, min(1.0, level))
        self.config["volume"] = level
        if self._tts_engine:
            self._tts_engine.setProperty("volume", level)
        self._save_config()
        return f"Voice volume set to {int(level * 100)}%."

    def set_voice_by_name(self, name: str) -> str:
        self.config["voice_name"] = name.lower()
        self._apply_pyttsx3_settings()
        self._save_config()
        return f"Trying to use voice: {name}. Say something to test it."

    def use_elevenlabs(self, voice_name: str = "makima") -> str:
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            return "Set ELEVENLABS_API_KEY in your .env file first."
        self.config["engine"] = "elevenlabs"
        self.config["elevenlabs_voice"] = voice_name
        self._save_config()
        return f"Switched to ElevenLabs voice: {voice_name}. Much more realistic!"

    def use_pyttsx3(self) -> str:
        self.config["engine"] = "pyttsx3"
        self._init_pyttsx3()
        self._save_config()
        return "Switched back to offline voice engine."

    def list_voices(self) -> str:
        if not self._tts_engine:
            return "Voice engine not available."
        voices = self._tts_engine.getProperty("voices")
        names = [v.name for v in voices[:10]]
        return "Available voices: " + ", ".join(names)

    def set_emotion(self, emotion: str):
        self._current_emotion = emotion

    def reset(self) -> str:
        self.config = dict(DEFAULT_CONFIG)
        self._init_engine()
        self._save_config()
        return "Voice reset to default settings."

    def get_status(self) -> str:
        return (
            f"Engine: {self.config['engine']}, "
            f"Speed: {self.config['speed']} WPM, "
            f"Volume: {int(self.config['volume']*100)}%, "
            f"Emotion modulation: {'on' if self.config['emotion_modulation'] else 'off'}."
        )
