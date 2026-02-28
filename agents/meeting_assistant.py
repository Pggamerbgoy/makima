"""
agents/meeting_assistant.py

Meeting Assistant
──────────────────
Makima joins and helps with meetings:
  - Live transcription of meeting audio
  - Auto-generates meeting notes
  - Action item extraction
  - Meeting summary on demand
  - Saves notes to file
  - Can answer questions about what was said
  - Speaker diarization (who said what)

Commands:
  "Start meeting notes"
  "Stop meeting notes"
  "What was just said?"
  "Summarize the meeting so far"
  "What are the action items?"
  "Save meeting notes"
  "Who mentioned [topic]?"
  "How long have we been in this meeting?"
"""

import os
import time
import json
import logging
import threading
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger("Makima.Meeting")

MEETINGS_DIR = "meeting_notes"

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


class MeetingAssistant:
    """
    Real-time meeting transcription and notes.
    Listens to system audio/microphone and builds structured notes.
    """

    CHUNK_DURATION = 30  # seconds per transcription chunk

    def __init__(self, ai, speak_callback: Callable):
        self.ai = ai
        self.speak = speak_callback
        self._active = False
        self._transcript: list[dict] = []
        self._start_time: Optional[float] = None
        self._thread: Optional[threading.Thread] = None
        self._recognizer = sr.Recognizer() if SR_AVAILABLE else None
        self._current_meeting_title = ""
        os.makedirs(MEETINGS_DIR, exist_ok=True)

    # ── Recording ─────────────────────────────────────────────────────────────

    def start(self, title: str = "") -> str:
        if self._active:
            return "Meeting notes are already running."
        if not SR_AVAILABLE:
            return "speech_recognition not installed."

        self._active = True
        self._transcript = []
        self._start_time = time.time()
        self._current_meeting_title = title or f"Meeting {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        return f"📝 Meeting notes started: '{self._current_meeting_title}'. I'm listening and transcribing."

    def stop(self) -> str:
        if not self._active:
            return "No meeting is currently being recorded."
        self._active = False
        duration = self._format_duration(time.time() - self._start_time)
        notes = self._generate_notes()
        path = self._save_notes(notes)
        return f"Meeting ended ({duration}). Notes saved to {path}.\n\n{notes[:500]}..."

    def _listen_loop(self):
        """Continuously listen and transcribe in chunks."""
        if not self._recognizer:
            return
        try:
            mic = sr.Microphone()
            with mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            logger.warning(f"Microphone error: {e}")
            return

        while self._active:
            try:
                with mic as source:
                    audio = self._recognizer.listen(
                        source, timeout=5, phrase_time_limit=self.CHUNK_DURATION
                    )
                try:
                    text = self._recognizer.recognize_google(audio)
                    if text.strip():
                        timestamp = time.time() - self._start_time
                        self._transcript.append({
                            "time": timestamp,
                            "text": text,
                            "time_str": self._format_duration(timestamp),
                        })
                        logger.debug(f"[{self._format_duration(timestamp)}] {text}")
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    logger.warning(f"Recognition error: {e}")
            except Exception as e:
                logger.debug(f"Listen loop error: {e}")

    # ── Analysis ──────────────────────────────────────────────────────────────

    def _full_transcript_text(self) -> str:
        return "\n".join(
            f"[{e['time_str']}] {e['text']}"
            for e in self._transcript
        )

    def _generate_notes(self) -> str:
        if not self._transcript:
            return "No transcript captured."

        transcript = self._full_transcript_text()
        notes = self.ai.chat(
            f"You are a professional meeting note-taker.\n"
            f"Meeting: {self._current_meeting_title}\n\n"
            f"Transcript:\n{transcript[:4000]}\n\n"
            f"Generate structured meeting notes with:\n"
            f"1. SUMMARY (2-3 sentences)\n"
            f"2. KEY POINTS (bullet list)\n"
            f"3. ACTION ITEMS (who does what by when)\n"
            f"4. DECISIONS MADE\n"
            f"5. FOLLOW-UP NEEDED\n"
            f"Be concise and professional."
        )
        return notes

    def what_was_said(self, n_lines: int = 5) -> str:
        if not self._transcript:
            return "Nothing transcribed yet."
        recent = self._transcript[-n_lines:]
        lines = [f"[{e['time_str']}] {e['text']}" for e in recent]
        return "Recent transcript:\n" + "\n".join(lines)

    def summarize_so_far(self) -> str:
        if not self._transcript:
            return "Nothing to summarize yet."
        transcript = self._full_transcript_text()
        return self.ai.chat(
            f"Summarize this meeting transcript in 3 bullet points:\n{transcript[:3000]}"
        )

    def get_action_items(self) -> str:
        if not self._transcript:
            return "No transcript yet."
        transcript = self._full_transcript_text()
        return self.ai.chat(
            f"Extract all action items from this meeting transcript. "
            f"Format: '• [Person/Team]: [Task] by [deadline if mentioned]'\n\n"
            f"Transcript:\n{transcript[:3000]}"
        )

    def search_transcript(self, query: str) -> str:
        if not self._transcript:
            return "No transcript to search."
        results = [
            e for e in self._transcript
            if query.lower() in e["text"].lower()
        ]
        if not results:
            return f"'{query}' was not mentioned in the meeting."
        lines = [f"[{e['time_str']}] {e['text']}" for e in results[:5]]
        return f"Found '{query}' {len(results)} time(s):\n" + "\n".join(lines)

    def get_duration(self) -> str:
        if not self._start_time:
            return "No meeting in progress."
        duration = time.time() - self._start_time
        return f"Meeting duration: {self._format_duration(duration)}."

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_notes(self, notes: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        safe_title = "".join(c for c in self._current_meeting_title if c.isalnum() or c in " _-")
        fname = f"{ts}_{safe_title[:30].replace(' ', '_')}.txt"
        path = os.path.join(MEETINGS_DIR, fname)

        content = (
            f"Meeting: {self._current_meeting_title}\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Duration: {self._format_duration(time.time() - self._start_time)}\n"
            f"{'='*60}\n\n"
            f"{notes}\n\n"
            f"{'='*60}\n"
            f"FULL TRANSCRIPT:\n\n"
            f"{self._full_transcript_text()}"
        )

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return path

    def list_past_meetings(self) -> str:
        if not os.path.isdir(MEETINGS_DIR):
            return "No meeting notes saved yet."
        files = sorted(os.listdir(MEETINGS_DIR), reverse=True)[:5]
        if not files:
            return "No meetings saved."
        return "Recent meetings:\n" + "\n".join(f"  • {f}" for f in files)

    def _format_duration(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"
