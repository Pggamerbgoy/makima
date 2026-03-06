"""
systems/music_dj.py

🎵 Background Music DJ — Full Implementation
──────────────────────────────────────────────
Core Features:
  • Mood-Based Playlists  (focus, hype, chill, sad, party, sleep, gaming, coding)
  • Activity Detection    (auto-plays music based on the active window/app)
  • Voice Control         (natural commands like "play something energetic")
  • Learning System       (remembers tracks you liked / skipped per mood)
  • Smart Volume          (adjusts Spotify volume based on mood / activity)
  • Listening History     (persists last 1000 tracks for taste profiling)

Requires:
  SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI  in .env
  pip install spotipy

Usage (from CommandRouter / voice):
    "play focus music"
    "play something energetic"
    "DJ mode on"
    "change mood to gaming"
    "what mood is playing"
    "like this song"
"""

import os
import re
import json
import random
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger("Makima.MusicDJ")

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

# ─── Persistent file paths ────────────────────────────────────────────────────

CONFIG_FILE  = "music_dj_config.json"
HISTORY_FILE = "music_dj_history.json"

# ─── Spotify OAuth scope (reuse creds from .env) ──────────────────────────────

SCOPE = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-read-currently-playing "
    "user-library-read "
    "user-library-modify "
    "playlist-read-private "
    "playlist-modify-private "
    "playlist-modify-public"
)

# ─── Mood Profiles ────────────────────────────────────────────────────────────
#
# Each mood defines:
#   genres        — Spotify seed genres used for recommendations
#   energy        — (min, max) 0.0–1.0
#   valence       — (min, max) happiness measure
#   instrumentalness / danceability / tempo — optional filters
#   keywords      — natural language triggers that map to this mood
#   default_vol   — smart volume level (0–100)

MOOD_PROFILES = {
    "focus": {
        "genres":             ["chill", "ambient", "classical", "study"],
        "energy":             (0.1, 0.45),
        "valence":            (0.2, 0.65),
        "instrumentalness":   (0.6, 1.0),
        "keywords":           [
            "focus", "study", "concentrate", "concentration",
            "deep work", "lofi", "lo-fi", "productive",
        ],
        "default_vol":        30,
    },
    "hype": {
        "genres":             ["edm", "hip-hop", "pop", "work-out"],
        "energy":             (0.7, 1.0),
        "valence":            (0.55, 1.0),
        "tempo":              (120, 180),
        "keywords":           [
            "hype", "workout", "energy", "energetic", "pump up",
            "motivation", "gym", "intense", "power",
        ],
        "default_vol":        65,
    },
    "chill": {
        "genres":             ["indie", "acoustic", "jazz", "soul", "r-n-b"],
        "energy":             (0.15, 0.55),
        "valence":            (0.35, 0.75),
        "keywords":           [
            "chill", "relax", "relaxing", "evening", "calm",
            "peaceful", "easy", "laid back", "wind down",
        ],
        "default_vol":        40,
    },
    "sad": {
        "genres":             ["indie", "acoustic", "alt-rock", "singer-songwriter"],
        "energy":             (0.1, 0.45),
        "valence":            (0.05, 0.35),
        "keywords":           [
            "sad", "melancholy", "emotional", "heartbreak",
            "depressed", "cry", "down", "blue", "lonely",
        ],
        "default_vol":        35,
    },
    "party": {
        "genres":             ["dance", "pop", "edm", "hip-hop", "party"],
        "energy":             (0.7, 1.0),
        "valence":            (0.65, 1.0),
        "danceability":       (0.65, 1.0),
        "keywords":           [
            "party", "dance", "celebrate", "fun", "club",
            "celebration", "Friday", "weekend",
        ],
        "default_vol":        75,
    },
    "sleep": {
        "genres":             ["ambient", "classical", "piano", "sleep"],
        "energy":             (0.0, 0.25),
        "valence":            (0.2, 0.55),
        "instrumentalness":   (0.75, 1.0),
        "keywords":           [
            "sleep", "sleeping", "meditation", "meditate",
            "peaceful", "night", "bedtime", "rest", "tired",
        ],
        "default_vol":        15,
    },
    "gaming": {
        "genres":             ["electronic", "rock", "metal", "dubstep"],
        "energy":             (0.6, 0.95),
        "valence":            (0.4, 0.85),
        "keywords":           [
            "gaming", "game", "epic", "intense", "action",
            "boss fight", "rpg", "battle",
        ],
        "default_vol":        55,
    },
    "coding": {
        "genres":             ["electronic", "chill", "ambient", "study"],
        "energy":             (0.3, 0.65),
        "instrumentalness":   (0.5, 1.0),
        "keywords":           [
            "coding", "programming", "hacker", "cyberpunk",
            "synthwave", "dev", "developer",
        ],
        "default_vol":        35,
    },
    "romantic": {
        "genres":             ["r-n-b", "soul", "jazz", "acoustic"],
        "energy":             (0.15, 0.5),
        "valence":            (0.45, 0.8),
        "keywords":           [
            "romantic", "love", "date", "romance",
            "candlelight", "slow dance",
        ],
        "default_vol":        35,
    },
}

# ─── Activity → Mood auto-mapping ─────────────────────────────────────────────
# Keys are substrings matched (case-insensitive) against the active window title
# or executable name.

ACTIVITY_MOOD_MAP = {
    # IDEs / editors
    "code":           "coding",
    "pycharm":        "coding",
    "visual studio":  "coding",
    "intellij":       "coding",
    "sublime":        "coding",
    "neovim":         "coding",
    "vim":            "coding",
    "terminal":       "coding",
    "powershell":     "coding",
    "cmd.exe":        "coding",

    # Gaming
    "steam":          "gaming",
    "epicgames":      "gaming",
    "riot client":    "gaming",
    "valorant":       "gaming",
    "minecraft":      "gaming",
    "genshin":        "gaming",
    "roblox":         "gaming",

    # Productivity
    "notion":         "focus",
    "obsidian":       "focus",
    "onenote":        "focus",
    "word":           "focus",
    "excel":          "focus",
    "powerpoint":     "focus",
    "docs.google":    "focus",

    # Social / chill
    "discord":        "chill",
    "spotify":        "chill",
    "youtube":        "chill",
    "netflix":        "chill",
    "twitch":         "chill",
}


# ═══════════════════════════════════════════════════════════════════════════════
# MusicDJ — Main class
# ═══════════════════════════════════════════════════════════════════════════════

class MusicDJ:
    """
    Intelligent Music DJ for Makima.
    Mood→playlist engine, activity-aware auto-DJ, learning + smart volume.
    """

    # ── Init ──────────────────────────────────────────────────────────────────

    def __init__(self, speak_callback: Callable = None,
                 preferences_manager=None):
        self.speak = speak_callback or (lambda t, **kw: None)
        self.prefs = preferences_manager

        self.sp: Optional[spotipy.Spotify] = None
        self.yt: Optional[object] = None # Will be set by setter or passed in
        self.current_mood: Optional[str] = None
        self.auto_dj_enabled: bool = False
        self._auto_dj_thread: Optional[threading.Thread] = None
        self._last_activity_app: Optional[str] = None
        self._stop_event = threading.Event()

        # Persistent data
        self.config: dict = {}
        self.history: list = []
        self.taste_profile: dict = {}  # mood → {liked: int, skipped: int}

        self._init_spotify()
        self._load_config()
        self._load_history()

        logger.info("🎵 MusicDJ initialized.")

    # ── Spotify Auth ──────────────────────────────────────────────────────────

    def _init_spotify(self):
        if not SPOTIPY_AVAILABLE:
            logger.warning("spotipy not installed — MusicDJ disabled.")
            return

        client_id     = os.getenv("SPOTIPY_CLIENT_ID")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        redirect_uri  = os.getenv("SPOTIPY_REDIRECT_URI",
                                  "http://localhost:8888/callback")

        if not client_id or not client_secret:
            logger.warning("Spotify credentials missing — MusicDJ disabled.")
            return

        try:
            auth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=SCOPE,
                open_browser=True,
            )
            self.sp = spotipy.Spotify(auth_manager=auth)
            logger.info("✅ MusicDJ Spotify connected.")
        except Exception as e:
            logger.warning(f"Spotify init failed for MusicDJ: {e}")

    def _check(self) -> Optional[str]:
        if not self.sp:
            return ("Spotify is not connected. "
                    "Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET in .env.")
        return None

    # ── Config / History Persistence ──────────────────────────────────────────

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception:
                self.config = {}

        # Ensure defaults
        self.config.setdefault("favorite_genres", [])
        self.config.setdefault("custom_playlists", {})
        self.config.setdefault("volume_overrides", {})
        self.config.setdefault("liked_track_ids", [])
        self.config.setdefault("skipped_track_ids", [])
        self.config.setdefault("auto_dj_enabled", False)

        self.auto_dj_enabled = self.config["auto_dj_enabled"]
        self.taste_profile = self.config.get("taste_profile", {})
        self._save_config()

    def _save_config(self):
        self.config["auto_dj_enabled"] = self.auto_dj_enabled
        self.config["taste_profile"]   = self.taste_profile
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save DJ config: {e}")

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
        else:
            self.history = []

    def _save_history_entry(self, track_name: str, artist: str, mood: str,
                            action: str = "played"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "track":     track_name,
            "artist":    artist,
            "mood":      mood,
            "action":    action,
        }
        self.history.append(entry)
        # Rolling window of 1000
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save DJ history: {e}")

    # ── Mood Detection from Natural Language ──────────────────────────────────

    def detect_mood(self, command: str) -> str:
        """Extract mood from a natural language music command."""
        text = command.lower().strip()

        # 1. Direct mood name match
        for mood in MOOD_PROFILES:
            if mood in text:
                return mood

        # 2. Keyword match — score each mood
        best_mood = "chill"
        best_score = 0
        for mood, profile in MOOD_PROFILES.items():
            score = sum(1 for kw in profile["keywords"] if kw in text)
            if score > best_score:
                best_score = score
                best_mood  = mood

        return best_mood

    # ── Track Search + Audio-Feature Filtering ────────────────────────────────

    def _search_tracks(self, mood: str, limit: int = 30) -> list:
        """Search Spotify for tracks matching a mood using recommendations API."""
        err = self._check()
        if err:
            return []

        profile = MOOD_PROFILES.get(mood, MOOD_PROFILES["chill"])
        genres  = profile["genres"]

        try:
            # Try the Recommendations API first (best quality)
            rec_kwargs = {
                "seed_genres": genres[:5],
                "limit":       limit,
            }
            # Map profile ranges to target values (midpoints)
            if "energy" in profile:
                lo, hi = profile["energy"]
                rec_kwargs["min_energy"]    = lo
                rec_kwargs["max_energy"]    = hi
                rec_kwargs["target_energy"] = (lo + hi) / 2
            if "valence" in profile:
                lo, hi = profile["valence"]
                rec_kwargs["min_valence"]    = lo
                rec_kwargs["max_valence"]    = hi
                rec_kwargs["target_valence"] = (lo + hi) / 2
            if "instrumentalness" in profile:
                lo, hi = profile["instrumentalness"]
                rec_kwargs["min_instrumentalness"] = lo
                rec_kwargs["target_instrumentalness"] = (lo + hi) / 2
            if "danceability" in profile:
                lo, hi = profile["danceability"]
                rec_kwargs["min_danceability"] = lo
                rec_kwargs["target_danceability"] = (lo + hi) / 2
            if "tempo" in profile:
                lo, hi = profile["tempo"]
                rec_kwargs["min_tempo"]    = lo
                rec_kwargs["max_tempo"]    = hi
                rec_kwargs["target_tempo"] = (lo + hi) / 2

            results = self.sp.recommendations(**rec_kwargs)
            tracks  = results.get("tracks", [])

            if tracks:
                # Boost tracks the user has previously liked
                liked_ids = set(self.config.get("liked_track_ids", []))
                # Sort: liked first, then random shuffle
                liked   = [t for t in tracks if t["id"] in liked_ids]
                others  = [t for t in tracks if t["id"] not in liked_ids]
                random.shuffle(others)
                return liked + others

        except Exception as e:
            logger.warning(f"Recommendations API failed: {e}")

        # Fallback: basic keyword search
        try:
            query   = " OR ".join(profile["keywords"][:3])
            results = self.sp.search(q=query, type="track", limit=limit)
            tracks  = results["tracks"]["items"]
            random.shuffle(tracks)
            return tracks
        except Exception as e:
            logger.warning(f"Search fallback failed: {e}")
            return []

    # ── Playback Control ──────────────────────────────────────────────────────

    def play_mood(self, mood: str) -> str:
        """Queue up tracks for a mood and start playback."""
        err = self._check()
        if err:
            # TRY YOUTUBE FALLBACK
            if self.yt:
                logger.info(f"Spotify unavailable, falling back to YouTube for mood: {mood}")
                # Use mood keywords as search query
                keywords = MOOD_PROFILES.get(mood, {}).get("keywords", [mood])
                query = random.choice(keywords) + " mix"
                return self.yt.play(query)
            return err

        profile = MOOD_PROFILES.get(mood)
        if not profile:
            return f"Unknown mood '{mood}'. Available: {', '.join(MOOD_PROFILES)}."

        try:
            devices = self.sp.devices()
            if not devices or not devices.get("devices"):
                return ("No active Spotify device found. "
                        "Open Spotify on your PC or phone first.")
        except Exception as e:
            return f"Could not reach Spotify devices: {e}"

        tracks = self._search_tracks(mood)
        if not tracks:
            return f"Couldn't find music for '{mood}' mood. Try another?"

        uris = [t["uri"] for t in tracks]

        try:
            self.sp.start_playback(uris=uris)
        except Exception as e:
            return f"Playback failed: {e}"

        # Smart volume
        vol = self.config.get("volume_overrides", {}).get(
            mood, profile.get("default_vol", 50)
        )
        try:
            self.sp.volume(vol)
        except Exception:
            pass  # Desktop app may not support volume control

        self.current_mood = mood
        first = tracks[0]
        name   = first["name"]
        artist = first["artists"][0]["name"]

        self._save_history_entry(name, artist, mood, "played")

        # Update taste profile
        self.taste_profile.setdefault(mood, {"played": 0, "liked": 0, "skipped": 0})
        self.taste_profile[mood]["played"] += 1
        self._save_config()

        return f"🎵 {mood.title()} vibes! Playing: {name} by {artist} (vol {vol}%)"

    def pause(self) -> str:
        err = self._check()
        if err: return err
        try:
            self.sp.pause_playback()
            return "⏸️ Music paused."
        except Exception:
            return "Nothing is currently playing."

    def resume(self) -> str:
        err = self._check()
        if err: return err
        try:
            self.sp.start_playback()
            return "▶️ Music resumed."
        except Exception:
            return "Couldn't resume playback."

    def skip(self) -> str:
        err = self._check()
        if err: return err
        try:
            # Record skip for learning
            current = self.sp.current_playback()
            if current and current.get("item"):
                tid = current["item"]["id"]
                if tid not in self.config.get("skipped_track_ids", []):
                    self.config.setdefault("skipped_track_ids", []).append(tid)
                if self.current_mood:
                    self.taste_profile.setdefault(
                        self.current_mood,
                        {"played": 0, "liked": 0, "skipped": 0}
                    )
                    self.taste_profile[self.current_mood]["skipped"] += 1
                self._save_config()

            self.sp.next_track()
            return "⏭️ Skipped."
        except Exception:
            return "Couldn't skip track."

    def previous(self) -> str:
        err = self._check()
        if err: return err
        try:
            self.sp.previous_track()
            return "⏮️ Going back."
        except Exception:
            return "Couldn't go back."

    def now_playing(self) -> str:
        err = self._check()
        if err: return err
        try:
            current = self.sp.current_playback()
            if current and current.get("is_playing") and current.get("item"):
                item   = current["item"]
                name   = item["name"]
                artist = ", ".join(a["name"] for a in item["artists"])
                mood_label = f" [{self.current_mood}]" if self.current_mood else ""
                vol = current.get("device", {}).get("volume_percent", "?")
                return f"🎶 Now playing: {name} by {artist}{mood_label} — Volume {vol}%"
            return "Nothing is playing right now."
        except Exception:
            return "Couldn't get current track info."

    def like_track(self) -> str:
        err = self._check()
        if err: return err
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return "Nothing is playing to like."
            item = current["item"]
            tid  = item["id"]
            name = item["name"]

            # Save to Spotify library
            self.sp.current_user_saved_tracks_add([tid])

            # Save to local config
            if tid not in self.config.get("liked_track_ids", []):
                self.config.setdefault("liked_track_ids", []).append(tid)

            # Update taste
            if self.current_mood:
                self.taste_profile.setdefault(
                    self.current_mood,
                    {"played": 0, "liked": 0, "skipped": 0}
                )
                self.taste_profile[self.current_mood]["liked"] += 1

            self._save_config()
            self._save_history_entry(name, item["artists"][0]["name"],
                                     self.current_mood or "unknown", "liked")
            return f"❤️ Liked '{name}'! I'll play more like this."
        except Exception as e:
            return f"Couldn't like track: {e}"

    def toggle_shuffle(self) -> str:
        err = self._check()
        if err: return err
        try:
            current = self.sp.current_playback()
            state   = current.get("shuffle_state", False)
            self.sp.shuffle(not state)
            return "🔀 Shuffle ON." if not state else "🔀 Shuffle OFF."
        except Exception:
            return "Couldn't toggle shuffle."

    # ── Volume (Spotify-level, not system) ────────────────────────────────────

    def set_volume(self, command: str) -> str:
        err = self._check()
        if err: return err

        try:
            current = self.sp.current_playback()
            cur_vol = current["device"]["volume_percent"]
        except Exception:
            cur_vol = 50

        new_vol = cur_vol

        if any(w in command for w in ("up", "louder", "increase")):
            new_vol = min(100, cur_vol + 10)
        elif any(w in command for w in ("down", "quieter", "decrease", "lower", "softer")):
            new_vol = max(0, cur_vol - 10)
        elif "mute" in command:
            new_vol = 0
        else:
            nums = re.findall(r"\d+", command)
            if nums:
                new_vol = max(0, min(100, int(nums[0])))

        try:
            self.sp.volume(new_vol)
            # persist override for current mood
            if self.current_mood:
                self.config.setdefault("volume_overrides", {})[self.current_mood] = new_vol
                self._save_config()
            return f"🔊 Volume set to {new_vol}%."
        except Exception:
            return "Couldn't adjust music volume."

    # ── Mood Change ───────────────────────────────────────────────────────────

    def change_mood(self, new_mood: str) -> str:
        if new_mood not in MOOD_PROFILES:
            return f"Unknown mood '{new_mood}'. Available: {', '.join(MOOD_PROFILES)}."
        return self.play_mood(new_mood)

    def get_current_mood(self) -> str:
        if self.current_mood:
            profile = MOOD_PROFILES[self.current_mood]
            return (f"Current mood: {self.current_mood.title()}\n"
                    f"  Genres: {', '.join(profile['genres'])}\n"
                    f"  Volume: {profile.get('default_vol', 50)}%")
        return "No mood is currently set. Tell me to play some music!"

    def list_moods(self) -> str:
        lines = []
        for mood, p in MOOD_PROFILES.items():
            lines.append(f"• {mood.title()} — {', '.join(p['genres'][:3])}")
        return "🎵 Available moods:\n" + "\n".join(lines)

    # ── DJ Stats / Learning Report ────────────────────────────────────────────

    def dj_stats(self) -> str:
        if not self.taste_profile:
            return "No listening data yet. Start playing some music first!"

        lines = ["🎵 Your Music Taste Profile:"]
        for mood, data in sorted(self.taste_profile.items(),
                                  key=lambda x: x[1].get("played", 0),
                                  reverse=True):
            played  = data.get("played", 0)
            liked   = data.get("liked", 0)
            skipped = data.get("skipped", 0)
            ratio   = f"{liked}/{played}" if played else "—"
            lines.append(f"  {mood.title():10s}  ▶ {played}  ❤ {liked}  ⏭ {skipped}  "
                         f"(like ratio {ratio})")

        total = len(self.config.get("liked_track_ids", []))
        lines.append(f"\nTotal liked songs: {total}")
        lines.append(f"History entries:   {len(self.history)}")
        return "\n".join(lines)

    # ── Activity Auto-DJ ──────────────────────────────────────────────────────

    def enable_auto_dj(self) -> str:
        if self.auto_dj_enabled and self._auto_dj_thread and self._auto_dj_thread.is_alive():
            return "Auto-DJ is already running."
        self.auto_dj_enabled = True
        self._stop_event.clear()
        self._auto_dj_thread = threading.Thread(
            target=self._auto_dj_loop, daemon=True, name="MusicDJ-AutoDJ"
        )
        self._auto_dj_thread.start()
        self._save_config()
        return "🎧 Auto-DJ enabled! I'll match music to whatever you're doing."

    def disable_auto_dj(self) -> str:
        self.auto_dj_enabled = False
        self._stop_event.set()
        self._save_config()
        return "🎧 Auto-DJ disabled."

    def _auto_dj_loop(self):
        """Background thread: polls active window and auto-switches mood."""
        logger.info("Auto-DJ loop started.")
        while not self._stop_event.is_set():
            try:
                app_name = self._detect_active_app()
                if app_name and app_name != self._last_activity_app:
                    self._last_activity_app = app_name
                    mood = self._mood_for_activity(app_name)
                    if mood and mood != self.current_mood:
                        result = self.play_mood(mood)
                        logger.info(f"Auto-DJ: {app_name} → {mood} — {result}")
                        if self.speak:
                            self.speak(f"Switching to {mood} music for {app_name}.")
            except Exception as e:
                logger.debug(f"Auto-DJ iteration error: {e}")

            # Poll every 10 seconds
            self._stop_event.wait(10)
        logger.info("Auto-DJ loop stopped.")

    @staticmethod
    def _detect_active_app() -> Optional[str]:
        """Get the currently active window title (Windows-only)."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value if buf.value else None
        except Exception:
            return None

    @staticmethod
    def _mood_for_activity(window_title: str) -> Optional[str]:
        """Map window title to a mood using ACTIVITY_MOOD_MAP."""
        title_lower = window_title.lower()
        for pattern, mood in ACTIVITY_MOOD_MAP.items():
            if pattern in title_lower:
                return mood
        return None

    # ── Master Command Handler ────────────────────────────────────────────────
    #
    # This is the single entry point called by CommandRouter handlers.
    # It parses the natural language command and dispatches internally.

    def handle_command(self, command: str) -> str:
        """Parse and execute a natural language music / DJ command."""
        cmd = command.lower().strip()

        # ── Play mood ──
        if re.search(r"(?:play|put on|start|give me)(?: some| me)? ", cmd):
            mood = self.detect_mood(cmd)
            return self.play_mood(mood)

        # ── Explicit mood change ──
        m = re.search(r"(?:change|switch|set) (?:mood|vibe) (?:to )?(\w+)", cmd)
        if m:
            return self.change_mood(m.group(1))

        # ── Pause / Stop ──
        if re.search(r"\b(?:pause|stop)\b", cmd):
            return self.pause()

        # ── Resume ──
        if re.search(r"\b(?:resume|continue|unpause)\b", cmd):
            return self.resume()

        # ── Skip ──
        if re.search(r"\b(?:skip|next)\b", cmd):
            return self.skip()

        # ── Previous ──
        if re.search(r"\b(?:previous|back|last track)\b", cmd):
            return self.previous()

        # ── What's playing ──
        if re.search(r"what(?:'s| is) playing|now playing|current (?:song|track)", cmd):
            return self.now_playing()

        # ── Like ──
        if re.search(r"\b(?:like|love|heart|save)\b.*(?:song|track|this)?", cmd):
            return self.like_track()

        # ── Shuffle ──
        if "shuffle" in cmd:
            return self.toggle_shuffle()

        # ── Volume ──
        if re.search(r"\b(?:volume|loud|quiet|mute|softer)\b", cmd):
            return self.set_volume(cmd)

        # ── Auto-DJ ──
        if re.search(r"(?:dj|auto.?dj|auto.?play|activity.?music).*(?:on|enable|start)", cmd):
            return self.enable_auto_dj()
        if re.search(r"(?:dj|auto.?dj|auto.?play|activity.?music).*(?:off|disable|stop)", cmd):
            return self.disable_auto_dj()

        # ── Stats ──
        if re.search(r"(?:dj|music|listening) (?:stats|report|taste|profile)", cmd):
            return self.dj_stats()

        # ── Mood info ──
        if re.search(r"(?:what|which) mood|current mood|what (?:mood|vibe)", cmd):
            return self.get_current_mood()

        # ── List moods ──
        if re.search(r"(?:list|show|available|all) moods?", cmd):
            return self.list_moods()

        # ── Fallback: try to detect mood from raw text ──
        mood = self.detect_mood(cmd)
        if mood != "chill":  # Non-default was detected
            return self.play_mood(mood)

        return self.play_mood("chill")
