"""
agents/emotion_detector.py

Emotion Detection from Voice
─────────────────────────────
Analyzes audio features from the user's voice to detect emotion:
  - Pitch / frequency → excitement, sadness
  - Energy / loudness → anger, enthusiasm
  - Speech rate → stress, calm
  - Spectral features → overall mood

Emotion states: happy, sad, angry, stressed, calm, excited, tired, neutral

Makima uses this to:
  - Adapt her tone and response style
  - Offer support when you sound stressed/sad
  - Match your energy when you're excited
  - Remind you to rest when you sound tired
"""

import os
import time
import logging
import threading
import numpy as np
from typing import Optional

logger = logging.getLogger("Makima.EmotionDetector")

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# Emotion → response style mapping
EMOTION_STYLES = {
    "happy":   {"tone": "warm and energetic",   "prefix": ""},
    "sad":     {"tone": "gentle and supportive", "prefix": "I noticed you might be feeling down. "},
    "angry":   {"tone": "calm and measured",     "prefix": "I'll keep things calm. "},
    "stressed": {"tone": "soothing",             "prefix": "Take a breath — I've got you. "},
    "excited": {"tone": "enthusiastic",          "prefix": ""},
    "tired":   {"tone": "concise and gentle",    "prefix": "You sound tired. Quick answer: "},
    "calm":    {"tone": "conversational",        "prefix": ""},
    "neutral": {"tone": "normal",                "prefix": ""},
}


class EmotionDetector:
    """
    Real-time voice emotion detection.
    Analyzes audio buffer after each user utterance.
    """

    SAMPLE_RATE = 22050
    WINDOW_SECONDS = 3  # Analyze last N seconds of speech

    def __init__(self, speak_callback=None):
        self.speak = speak_callback
        self.current_emotion = "neutral"
        self.emotion_history: list[str] = []
        self._audio_buffer: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False

        if not SD_AVAILABLE:
            logger.warning("sounddevice not installed. Emotion detection disabled.")
            logger.warning("Install: pip install sounddevice")
        if not LIBROSA_AVAILABLE:
            logger.warning("librosa not installed. Emotion detection disabled.")
            logger.warning("Install: pip install librosa")

    # ─── Feature Extraction ───────────────────────────────────────────────────

    def analyze_audio(self, audio: np.ndarray, sr: int = SAMPLE_RATE) -> str:
        """
        Extract features from audio and classify emotion.
        Uses pitch, energy, zero-crossing rate, and MFCCs.
        """
        if not LIBROSA_AVAILABLE or audio is None or len(audio) == 0:
            return "neutral"

        try:
            audio = audio.astype(np.float32)
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            # ── Feature 1: Pitch (F0) ──
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
            pitch_values = pitches[magnitudes > magnitudes.mean()]
            mean_pitch = np.mean(pitch_values) if len(pitch_values) > 0 else 0
            pitch_std = np.std(pitch_values) if len(pitch_values) > 0 else 0

            # ── Feature 2: Energy (RMS) ──
            rms = librosa.feature.rms(y=audio)[0]
            mean_energy = np.mean(rms)
            energy_std = np.std(rms)

            # ── Feature 3: Zero Crossing Rate (speech rate proxy) ──
            zcr = librosa.feature.zero_crossing_rate(audio)[0]
            mean_zcr = np.mean(zcr)

            # ── Feature 4: MFCCs (spectral shape) ──
            mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            mfcc_means = np.mean(mfccs, axis=1)

            # ── Rule-based classifier ──
            emotion = self._classify(
                mean_pitch=mean_pitch,
                pitch_std=pitch_std,
                mean_energy=mean_energy,
                energy_std=energy_std,
                mean_zcr=mean_zcr,
                mfcc_means=mfcc_means,
            )
            return emotion

        except Exception as e:
            logger.debug(f"Emotion analysis error: {e}")
            return "neutral"

    def _classify(self, mean_pitch, pitch_std, mean_energy,
                  energy_std, mean_zcr, mfcc_means) -> str:
        """
        Rule-based emotion classification from audio features.
        These thresholds are calibrated for typical speech.
        """
        # Normalize features to rough 0-1 scale
        energy_norm = min(mean_energy * 10, 1.0)
        pitch_norm = min(mean_pitch / 500, 1.0)
        rate_norm = min(mean_zcr * 20, 1.0)

        # Anger: high energy + low-mid pitch + high variation
        if energy_norm > 0.7 and energy_std > 0.03 and pitch_norm < 0.6:
            return "angry"

        # Excited: high pitch + high energy + fast rate
        if pitch_norm > 0.7 and energy_norm > 0.5 and rate_norm > 0.6:
            return "excited"

        # Happy: high-mid pitch + moderate-high energy + stable
        if pitch_norm > 0.5 and energy_norm > 0.4 and pitch_std < 100:
            return "happy"

        # Stressed: high rate + moderate energy + erratic pitch
        if rate_norm > 0.7 and pitch_std > 80:
            return "stressed"

        # Sad: low pitch + low energy + slow rate
        if pitch_norm < 0.3 and energy_norm < 0.25 and rate_norm < 0.3:
            return "sad"

        # Tired: very low energy + slow rate + low pitch
        if energy_norm < 0.15 and rate_norm < 0.25:
            return "tired"

        # Calm: moderate everything
        if 0.3 < energy_norm < 0.5 and rate_norm < 0.5:
            return "calm"

        return "neutral"

    # ─── Integration with Speech ──────────────────────────────────────────────

    def analyze_speech_segment(self, audio_data: np.ndarray, sr: int) -> str:
        """Called after each user utterance. Returns detected emotion."""
        emotion = self.analyze_audio(audio_data, sr)
        self._update_emotion(emotion)
        return emotion

    def _update_emotion(self, emotion: str):
        """Update current emotion with smoothing (avoid flickering)."""
        self.emotion_history.append(emotion)
        if len(self.emotion_history) > 5:
            self.emotion_history.pop(0)

        # Use most common recent emotion
        from collections import Counter
        counts = Counter(self.emotion_history)
        dominant = counts.most_common(1)[0][0]

        if dominant != self.current_emotion:
            prev = self.current_emotion
            self.current_emotion = dominant
            logger.info(f"😊 Emotion changed: {prev} → {dominant}")
            self._on_emotion_change(prev, dominant)

    def _on_emotion_change(self, previous: str, current: str):
        """React to significant emotion changes."""
        if current == "sad" and self.speak:
            self.speak("Hey, are you okay? I'm here if you need to talk.")
        elif current == "stressed" and self.speak:
            self.speak("You sound a bit stressed. Take it easy — I'll keep my answers short.")
        elif current == "tired" and self.speak:
            self.speak("You sound tired. Maybe take a short break?")

    # ─── Public Interface ─────────────────────────────────────────────────────

    def get_style(self) -> dict:
        """Get current response style based on emotion."""
        return EMOTION_STYLES.get(self.current_emotion, EMOTION_STYLES["neutral"])

    def get_prefix(self) -> str:
        """Get empathetic prefix for current emotion."""
        return self.get_style().get("prefix", "")

    def describe_emotion(self) -> str:
        return f"Based on your voice, you seem {self.current_emotion} right now."

    def get_current(self) -> str:
        return self.current_emotion

    def emotion_adapted_prompt(self, base_prompt: str) -> str:
        """Inject emotion context into AI prompt."""
        style = self.get_style()
        emotion_context = (
            f"\n[User's current emotional state: {self.current_emotion}. "
            f"Adjust your tone to be {style['tone']}.]"
        )
        return base_prompt + emotion_context
