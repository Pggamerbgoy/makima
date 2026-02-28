"""
systems/spotify_control.py
Control Spotify playback via the Spotipy library (Spotify Web API).
Requires SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI env vars.
"""

import os
import logging

logger = logging.getLogger("Makima.Spotify")

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False


SCOPE = (
    "user-read-playback-state user-modify-playback-state "
    "user-read-currently-playing playlist-read-private"
)


class SpotifyControl:

    def __init__(self):
        self.sp = None
        self._init()

    def _init(self):
        if not SPOTIPY_AVAILABLE:
            logger.warning("spotipy not installed. Spotify disabled.")
            return

        client_id = os.getenv("SPOTIPY_CLIENT_ID")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")

        if not client_id or not client_secret:
            logger.warning("Spotify credentials not set. Spotify disabled.")
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
            logger.info("✅ Spotify connected.")
        except Exception as e:
            logger.warning(f"Spotify init failed: {e}")

    def _check(self) -> str | None:
        if not self.sp:
            return "Spotify is not connected. Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET."
        return None

    def play(self, query: str = None) -> str:
        err = self._check()
        if err:
            return err
        try:
            if query:
                return self.play_song(query)
            self.sp.start_playback()
            return "Playing Spotify."
        except Exception as e:
            return f"Couldn't play: {e}"

    def pause(self) -> str:
        err = self._check()
        if err:
            return err
        try:
            self.sp.pause_playback()
            return "Paused."
        except Exception as e:
            return f"Couldn't pause: {e}"

    def next_track(self) -> str:
        err = self._check()
        if err:
            return err
        try:
            self.sp.next_track()
            return "Skipped to next track."
        except Exception as e:
            return f"Couldn't skip: {e}"

    def prev_track(self) -> str:
        err = self._check()
        if err:
            return err
        try:
            self.sp.previous_track()
            return "Going back."
        except Exception as e:
            return f"Couldn't go back: {e}"

    def current_track(self) -> str:
        err = self._check()
        if err:
            return err
        try:
            ct = self.sp.current_playback()
            if ct and ct.get("item"):
                item = ct["item"]
                artists = ", ".join(a["name"] for a in item["artists"])
                return f"Now playing: {item['name']} by {artists}."
            return "Nothing is playing right now."
        except Exception as e:
            return f"Couldn't get current track: {e}"

    def play_song(self, query: str) -> str:
        err = self._check()
        if err:
            return err
        try:
            results = self.sp.search(q=query, type="track", limit=1)
            tracks = results["tracks"]["items"]
            if not tracks:
                return f"Couldn't find '{query}' on Spotify."
            uri = tracks[0]["uri"]
            name = tracks[0]["name"]
            artists = ", ".join(a["name"] for a in tracks[0]["artists"])
            self.sp.start_playback(uris=[uri])
            return f"Playing {name} by {artists}."
        except Exception as e:
            return f"Spotify search failed: {e}"
