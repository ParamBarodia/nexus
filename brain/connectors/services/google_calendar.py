"""Google Calendar connector — today's events and upcoming schedule via Google Calendar API (OAuth2)."""

import os
import logging
from datetime import datetime, timedelta, timezone

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.google_calendar")


class GoogleCalendarConnector(BaseConnector):
    name = "google_calendar"
    description = "Google Calendar — today's agenda and upcoming events"
    category = "personal"
    poll_interval_minutes = 15
    required_env = []

    def _get_service(self):
        """Build the Google Calendar API service using stored OAuth2 credentials."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            raise RuntimeError(
                "google-auth-oauthlib and google-api-python-client are required. "
                "Install with: pip install google-auth-oauthlib google-api-python-client"
            )

        token = get_credential("google", "access_token")
        refresh_token = get_credential("google", "refresh_token")
        client_id = get_credential("google", "client_id")
        client_secret = get_credential("google", "client_secret")

        if not token and not refresh_token:
            raise RuntimeError(
                "Google OAuth2 credentials not configured. "
                "Store credentials via: brain.connectors.auth.store_credential('google', 'access_token', ...)"
            )

        creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id or os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=client_secret or os.getenv("GOOGLE_CLIENT_SECRET", ""),
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )
        return build("calendar", "v3", credentials=creds)

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "today")

        cached = self._cache_get(f"gcal_{action}")
        if cached:
            return cached

        try:
            service = self._get_service()
        except RuntimeError as e:
            return {"error": str(e), "action": action, "events": []}

        now = datetime.now(timezone.utc)

        if action == "upcoming":
            time_min = now.isoformat()
            time_max = (now + timedelta(days=7)).isoformat()
        else:
            # today
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            time_min = start_of_day.isoformat()
            time_max = (start_of_day + timedelta(days=1)).isoformat()

        try:
            result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=20,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = []
            for ev in result.get("items", []):
                start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", ""))
                events.append({
                    "summary": ev.get("summary", "(No title)"),
                    "start": start,
                    "location": ev.get("location", ""),
                    "status": ev.get("status", ""),
                })
            data = {"action": action, "events": events}
        except Exception as e:
            logger.error("Google Calendar API error: %s", e)
            data = {"action": action, "events": [], "error": str(e)}

        self._cache_set(f"gcal_{action}", data)
        return data

    def briefing_summary(self, data: dict) -> str:
        events = data.get("events", [])
        if data.get("error"):
            return f"Calendar: {data['error']}"
        if not events:
            return "No calendar events today."
        lines = [f"Calendar ({data.get('action', 'today')}):"]
        for ev in events[:8]:
            time_str = ev["start"]
            if "T" in time_str:
                try:
                    t = datetime.fromisoformat(time_str)
                    time_str = t.strftime("%H:%M")
                except ValueError:
                    pass
            lines.append(f"  - {time_str} {ev['summary']}")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "gcal_today",
                "description": "Get today's Google Calendar events.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "today"}),
            },
            {
                "name": "gcal_upcoming",
                "description": "Get upcoming Google Calendar events for the next 7 days.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "upcoming"}),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
