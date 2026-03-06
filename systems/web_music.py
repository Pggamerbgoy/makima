"""
systems/web_music.py
Browser-based music playback for YouTube and Spotify Web.
"""

import webbrowser
import logging
import urllib.parse

logger = logging.getLogger("Makima.WebMusic")

class WebMusic:
    """Handles opening music links in the preferred browser."""

    YOUTUBE_SEARCH = "https://www.youtube.com/results?search_query="
    SPOTIFY_WEB_SEARCH = "https://open.spotify.com/search/"

    def __init__(self, prefs=None):
        self._prefs = prefs

    def _get_browser(self):
        """Get the preferred browser from preferences."""
        if self._prefs:
            pref = self._prefs.get_preference("browser")
            if pref:
                try:
                    return webbrowser.get(pref)
                except webbrowser.Error:
                    logger.warning(f"Browser '{pref}' not found. Falling back to default.")
        return webbrowser

    def search_youtube(self, query: str) -> str:
        """Open YouTube search results in browser."""
        if not query:
            return "What would you like to search for on YouTube?"
        encoded_query = urllib.parse.quote(query)
        url = f"{self.YOUTUBE_SEARCH}{encoded_query}"
        self._get_browser().open(url)
        return f"Searching for '{query}' on YouTube."

    def open_url(self, url: str, title: str = "") -> str:
        """Open a specific URL in the browser."""
        if not url:
            return "No URL provided."
        self._get_browser().open(url)
        return f"Opening {title or url} in your browser."

    def play_youtube(self, query: str) -> str:
        """Legacy method - defaults to search."""
        return self.search_youtube(query)

    def play_web_spotify(self, query: str) -> str:
        """Search and play a song on Spotify Web."""
        if not query:
            return "What would you like to play on Spotify Web?"
        
        encoded_query = urllib.parse.quote(query)
        url = f"{self.SPOTIFY_WEB_SEARCH}{encoded_query}"
        self._get_browser().open(url)
        return f"Opening '{query}' on Spotify Web."

    def play_any(self, query: str) -> str:
        """Default to YouTube if platform not specified."""
        return self.play_youtube(query)
