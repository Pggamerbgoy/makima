"""
systems/daily_briefing.py

Smart Daily Briefing
─────────────────────
One command → complete personalised morning briefing:

  1. 🌤  Weather — current + today's forecast
  2. 📅  Calendar — today's events and reminders
  3. 📧  Emails — unread count + priority emails
  4. 📰  News — top 3 headlines (configurable topics)
  5. 🔋  System — battery, CPU health
  6. 📊  Habit streak — how you're doing on tracked habits
  7. 💬  Personal note — Makima's personalised message based on all the above

Commands:
  "Good morning" / "Morning briefing"
  "Evening briefing"
  "What's today look like?"
  "Quick briefing"          → shorter version
  "Full briefing"           → everything
  "Briefing settings"       → configure what to include
"""

import os
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("Makima.DailyBriefing")

BRIEFING_CONFIG_FILE = "briefing_config.json"

DEFAULT_CONFIG = {
    "include_weather": True,
    "include_calendar": True,
    "include_email": True,
    "include_news": True,
    "include_system": True,
    "include_habits": True,
    "news_topics": ["technology", "world"],
    "weather_city": "",           # auto-detect if empty
    "briefing_style": "full",     # "full" | "quick" | "bullet"
    "personal_message": True,     # AI-generated personal note at end
}


class DailyBriefing:
    """Assembles and delivers a personalised daily briefing."""

    def __init__(self, ai, memory=None, reminder_system=None):
        self.ai = ai
        self.memory = memory
        self.reminders = reminder_system
        self.config = self._load_config()
        self._last_briefing_date: Optional[str] = None

    def _load_config(self) -> dict:
        if os.path.exists(BRIEFING_CONFIG_FILE):
            try:
                with open(BRIEFING_CONFIG_FILE) as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def _save_config(self):
        with open(BRIEFING_CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    # ── Data Gathering ────────────────────────────────────────────────────────

    def _get_weather(self) -> str:
        city = self.config.get("weather_city", "")
        try:
            import requests
            # Open-Meteo — free, no API key
            if not city:
                # Try IP-based location
                loc = requests.get("https://ipapi.co/json/", timeout=5).json()
                lat = loc.get("latitude", 28.6)
                lon = loc.get("longitude", 77.2)
                city = loc.get("city", "your city")
            else:
                # Geocode city name
                geo = requests.get(
                    f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1",
                    timeout=5
                ).json()
                result = geo.get("results", [{}])[0]
                lat = result.get("latitude", 28.6)
                lon = result.get("longitude", 77.2)

            weather = requests.get(
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current_weather=true"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
                f"&timezone=auto&forecast_days=1",
                timeout=5
            ).json()

            current = weather.get("current_weather", {})
            daily = weather.get("daily", {})
            temp = current.get("temperature", "?")
            code = current.get("weathercode", 0)
            wind = current.get("windspeed", 0)

            condition = self._weather_code_to_text(code)
            max_t = daily.get("temperature_2m_max", ["?"])[0]
            min_t = daily.get("temperature_2m_min", ["?"])[0]
            rain = daily.get("precipitation_sum", [0])[0]

            rain_note = f", {rain}mm rain expected" if rain > 0 else ""
            return (
                f"🌤 {city}: {temp}°C, {condition}. "
                f"Today: {min_t}°–{max_t}°C, wind {wind} km/h{rain_note}."
            )
        except Exception as e:
            logger.debug(f"Weather error: {e}")
            return "🌤 Weather unavailable right now."

    def _weather_code_to_text(self, code: int) -> str:
        if code == 0: return "clear sky"
        if code <= 3: return "partly cloudy"
        if code <= 48: return "foggy"
        if code <= 67: return "rainy"
        if code <= 77: return "snowy"
        if code <= 82: return "showers"
        return "stormy"

    def _get_calendar(self) -> str:
        today = datetime.now()
        day_name = today.strftime("%A, %B %d")
        lines = [f"📅 Today is {day_name}."]

        if self.reminders:
            active = [r for r in self.reminders._reminders if not r["fired"]]
            if active:
                for r in active[:3]:
                    time_str = r["time"].strftime("%I:%M %p")
                    lines.append(f"  ⏰ {time_str}: {r['task']}")
            else:
                lines.append("  No reminders set for today.")

        return "\n".join(lines)

    def _get_email_summary(self) -> str:
        addr = os.getenv("EMAIL_ADDRESS", "")
        if not addr:
            return ""
        try:
            import imaplib
            imap = imaplib.IMAP4_SSL(
                os.getenv("IMAP_SERVER", "imap.gmail.com"),
                int(os.getenv("IMAP_PORT", "993"))
            )
            imap.login(addr, os.getenv("EMAIL_PASSWORD", ""))
            imap.select("INBOX")
            _, data = imap.search(None, "(UNSEEN)")
            count = len(data[0].split()) if data[0] else 0
            imap.logout()
            if count == 0:
                return "📧 Inbox clear — no unread emails."
            return f"📧 {count} unread email{'s' if count != 1 else ''} in your inbox."
        except Exception:
            return ""

    def _get_news(self) -> str:
        topics = self.config.get("news_topics", ["technology"])
        try:
            import requests
            headlines = []
            for topic in topics[:2]:
                resp = requests.get(
                    f"https://newsdata.io/api/1/news"
                    f"?apikey={os.getenv('NEWSDATA_API_KEY','')}"
                    f"&q={topic}&language=en&size=2",
                    timeout=5
                )
                if resp.status_code == 200:
                    articles = resp.json().get("results", [])
                    for a in articles[:2]:
                        headlines.append(a.get("title", ""))

            if not headlines:
                # Fallback: GNews (free tier)
                resp = requests.get(
                    "https://gnews.io/api/v4/top-headlines"
                    f"?token={os.getenv('GNEWS_API_KEY','')}&lang=en&max=3",
                    timeout=5
                )
                if resp.status_code == 200:
                    articles = resp.json().get("articles", [])
                    headlines = [a.get("title", "") for a in articles[:3]]

            if headlines:
                lines = ["📰 Top headlines:"]
                for h in headlines[:3]:
                    lines.append(f"  • {h[:80]}")
                return "\n".join(lines)
        except Exception as e:
            logger.debug(f"News error: {e}")
        return "📰 News unavailable (set GNEWS_API_KEY for headlines)."

    def _get_system_status(self) -> str:
        try:
            import psutil
            batt = psutil.sensors_battery()
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            parts = [f"💻 CPU {cpu:.0f}%, RAM {mem.percent:.0f}%"]
            if batt:
                plug = "charging" if batt.power_plugged else "on battery"
                parts.append(f"🔋 {batt.percent:.0f}% ({plug})")
            return ", ".join(parts) + "."
        except Exception:
            return ""

    # ── Briefing Assembly ─────────────────────────────────────────────────────

    def _gather_all(self) -> dict:
        """Gather all briefing components in parallel."""
        data = {}
        tasks = []
        results = {}

        def run(key, fn):
            try:
                results[key] = fn()
            except Exception as e:
                results[key] = ""
                logger.debug(f"Briefing {key} error: {e}")

        cfg = self.config
        if cfg["include_weather"]:
            t = threading.Thread(target=run, args=("weather", self._get_weather), daemon=True)
            tasks.append(t)
        if cfg["include_calendar"]:
            t = threading.Thread(target=run, args=("calendar", self._get_calendar), daemon=True)
            tasks.append(t)
        if cfg["include_email"]:
            t = threading.Thread(target=run, args=("email", self._get_email_summary), daemon=True)
            tasks.append(t)
        if cfg["include_news"]:
            t = threading.Thread(target=run, args=("news", self._get_news), daemon=True)
            tasks.append(t)
        if cfg["include_system"]:
            t = threading.Thread(target=run, args=("system", self._get_system_status), daemon=True)
            tasks.append(t)

        for t in tasks:
            t.start()
        for t in tasks:
            t.join(timeout=8)

        return results

    def deliver(self, style: str = None) -> str:
        """Build and return the full briefing."""
        style = style or self.config.get("briefing_style", "full")
        now = datetime.now()
        hour = now.hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

        data = self._gather_all()
        sections = [f"{greeting}! Here's your briefing for {now.strftime('%A, %B %d')}."]

        for key in ["weather", "calendar", "email", "system", "news"]:
            val = data.get(key, "")
            if val:
                sections.append(val)

        if style == "quick":
            # Just weather + calendar + email
            parts = [sections[0]]
            parts += [s for s in sections[1:] if any(e in s for e in ["🌤", "📅", "📧"])]
            briefing_text = "\n".join(parts)
        else:
            briefing_text = "\n".join(sections)

        # Personal AI message at end
        if self.config.get("personal_message", True) and style != "quick":
            context = "\n".join(sections)
            personal, _ = self.ai.chat(
                f"Based on this morning briefing data:\n{context}\n\n"
                f"Write one short, warm, personal sentence as Makima — "
                f"an encouraging or insightful note tailored to what the user is facing today. "
                f"Max 20 words. No generic advice."
            )
            if personal:
                briefing_text += f"\n\n💜 {personal}"

        self._last_briefing_date = now.strftime("%Y-%m-%d")
        return briefing_text

    def quick(self) -> str:
        return self.deliver(style="quick")

    # ── Configuration ─────────────────────────────────────────────────────────

    def set_city(self, city: str) -> str:
        self.config["weather_city"] = city
        self._save_config()
        return f"Weather city set to {city}."

    def add_news_topic(self, topic: str) -> str:
        topics = self.config.setdefault("news_topics", [])
        if topic not in topics:
            topics.append(topic)
        self._save_config()
        return f"Added '{topic}' to your news topics."

    def toggle(self, section: str, enabled: bool) -> str:
        key = f"include_{section}"
        if key in self.config:
            self.config[key] = enabled
            self._save_config()
            return f"{'Included' if enabled else 'Excluded'} {section} from briefing."
        return f"Unknown section: {section}"

    def set_style(self, style: str) -> str:
        if style in ("full", "quick", "bullet"):
            self.config["briefing_style"] = style
            self._save_config()
            return f"Briefing style set to {style}."
        return "Style must be: full, quick, or bullet."
