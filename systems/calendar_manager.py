"""
systems/calendar_manager.py

Google Calendar Integration
────────────────────────────
Lazy-loaded to keep startup fast.
Requires:
  • credentials.json in the project root (Google OAuth client secret)
  • Set CALENDAR_ENABLED=1 in your .env to activate on startup

Commands routed here (via command_router):
  "what's on my calendar"       → reads upcoming events
  "add event [title] at [time]" → creates a new event
  "my schedule today"           → today's events

Dependencies (add to requirements.txt if needed):
  google-api-python-client
  google-auth-oauthlib
  google-auth-httplib2
"""

import os
import pickle
import logging
import datetime

logger = logging.getLogger("Makima.Calendar")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

TOKEN_FILE = "token.pickle"
CREDENTIALS_FILE = "credentials.json"


class CalendarManager:
    """Google Calendar integration — read and create events."""

    def __init__(self):
        self.service = None
        self._enabled = os.getenv("CALENDAR_ENABLED", "0") == "1"
        if self._enabled:
            self._authenticate()
        else:
            logger.info("Calendar disabled — set CALENDAR_ENABLED=1 to enable.")

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _authenticate(self):
        """OAuth2 flow — caches token to token.pickle for subsequent runs."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            logger.warning(
                "Google API packages not installed. "
                "Run: pip install google-api-python-client google-auth-oauthlib"
            )
            return

        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as tok:
                creds = pickle.load(tok)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            elif os.path.exists(CREDENTIALS_FILE):
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                logger.warning(
                    f"{CREDENTIALS_FILE} not found — Google Calendar unavailable."
                )
                return
            with open(TOKEN_FILE, "wb") as tok:
                pickle.dump(creds, tok)

        try:
            from googleapiclient.discovery import build
            self.service = build("calendar", "v3", credentials=creds)
            logger.info("✅ Google Calendar connected.")
        except Exception as e:
            logger.error(f"Calendar service build error: {e}")

    # ── Queries ───────────────────────────────────────────────────────────────

    def _require_service(self) -> bool:
        if not self.service:
            return False
        return True

    def get_upcoming_events(self, max_results: int = 5) -> str:
        """Return a human-readable string of upcoming calendar events."""
        if not self._require_service():
            return "Calendar is not connected. Set CALENDAR_ENABLED=1 and add credentials.json."

        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"
            result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = result.get("items", [])

            if not events:
                return "You have no upcoming events."

            lines = [f"You have {len(events)} upcoming event(s):"]
            for ev in events:
                start = ev["start"].get("dateTime", ev["start"].get("date", ""))
                summary = ev.get("summary", "Untitled")
                try:
                    dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                    date_str = dt.strftime("%A, %B %d")
                    time_str = dt.strftime("%I:%M %p")
                    lines.append(f" • {summary} — {date_str} at {time_str}")
                except Exception:
                    lines.append(f" • {summary}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Calendar fetch error: {e}")
            return "Could not retrieve calendar events."

    def get_todays_events(self) -> str:
        """Return events occurring today."""
        if not self._require_service():
            return "Calendar is not connected."

        try:
            today = datetime.date.today()
            start = datetime.datetime(today.year, today.month, today.day).isoformat() + "Z"
            end = (
                datetime.datetime(today.year, today.month, today.day, 23, 59, 59).isoformat()
                + "Z"
            )
            result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=start,
                    timeMax=end,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = result.get("items", [])
            if not events:
                return "You have nothing scheduled for today."

            lines = [f"Today's schedule ({today.strftime('%A, %B %d')}):"]
            for ev in events:
                time_raw = ev["start"].get("dateTime", "")
                summary = ev.get("summary", "Untitled")
                try:
                    dt = datetime.datetime.fromisoformat(time_raw.replace("Z", "+00:00"))
                    lines.append(f" • {dt.strftime('%I:%M %p')} — {summary}")
                except Exception:
                    lines.append(f" • {summary}")
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Today's events error: {e}")
            return "Could not retrieve today's schedule."

    def get_events_summary(self, max_results: int = 5) -> list[str]:
        """Return events as a plain list of strings (for use in briefings etc.)."""
        if not self._require_service():
            return ["Calendar not connected."]
        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"
            result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = result.get("items", [])
            if not events:
                return ["No upcoming events."]
            out = []
            for ev in events:
                start = ev["start"].get("dateTime", ev["start"].get("date", ""))
                summary = ev.get("summary", "Untitled")
                try:
                    dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                    out.append(f"{summary} at {dt.strftime('%I:%M %p')}")
                except Exception:
                    out.append(summary)
            return out
        except Exception as e:
            logger.error(f"Event summary error: {e}")
            return ["Could not retrieve calendar."]

    # ── Mutations ─────────────────────────────────────────────────────────────

    def add_event(self, summary: str, start_dt: datetime.datetime, duration_minutes: int = 60) -> str:
        """Create a calendar event starting at start_dt."""
        if not self._require_service():
            return "Calendar is not connected."
        try:
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
            event = {
                "summary": summary,
                "start": {
                    "dateTime": start_dt.isoformat() + "Z",
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": end_dt.isoformat() + "Z",
                    "timeZone": "UTC",
                },
            }
            created = self.service.events().insert(calendarId="primary", body=event).execute()
            logger.info(f"Event created: {created.get('htmlLink')}")
            return f"Event '{summary}' added to your calendar."
        except Exception as e:
            logger.error(f"Add event error: {e}")
            return "Could not create the event."

    # ── Command dispatcher ────────────────────────────────────────────────────

    def handle_command(self, command: str) -> str | None:
        """
        Lightweight dispatcher — called from CommandRouter.
        Returns a response string or None if command not recognised.
        """
        cmd = command.lower()
        if any(kw in cmd for kw in ("today's schedule", "schedule today", "today")):
            return self.get_todays_events()
        if any(kw in cmd for kw in ("calendar", "events", "schedule", "upcoming")):
            return self.get_upcoming_events()
        return None
