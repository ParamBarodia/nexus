"""Google Tasks connector — list and add tasks via Google Tasks API (OAuth2 shared with Google)."""

import os
import logging

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.google_tasks")


class GoogleTasksConnector(BaseConnector):
    name = "google_tasks"
    description = "Google Tasks — list, view, and add tasks"
    category = "personal"
    poll_interval_minutes = 30
    required_env = []

    def _get_service(self):
        """Build the Google Tasks API service using stored OAuth2 credentials."""
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
            scopes=["https://www.googleapis.com/auth/tasks"],
        )
        return build("tasks", "v1", credentials=creds)

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "list")

        if action == "list":
            cached = self._cache_get("gtasks_list")
            if cached:
                return cached

        try:
            service = self._get_service()
        except RuntimeError as e:
            return {"error": str(e), "action": action, "tasks": []}

        try:
            if action == "add":
                title = params.get("title", "New task")
                notes = params.get("notes", "")
                tasklist_id = params.get("tasklist", "@default")
                body = {"title": title}
                if notes:
                    body["notes"] = notes
                result = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
                data = {
                    "action": "add",
                    "created": {
                        "id": result.get("id", ""),
                        "title": result.get("title", ""),
                        "status": result.get("status", ""),
                    },
                }
            else:
                # list tasks
                tasklist_id = params.get("tasklist", "@default")
                result = service.tasks().list(
                    tasklist=tasklist_id, maxResults=20, showCompleted=False
                ).execute()
                tasks = []
                for t in result.get("items", []):
                    tasks.append({
                        "title": t.get("title", ""),
                        "status": t.get("status", ""),
                        "due": t.get("due", ""),
                        "notes": t.get("notes", ""),
                    })
                data = {"action": "list", "tasks": tasks}
                self._cache_set("gtasks_list", data)

        except Exception as e:
            logger.error("Google Tasks API error: %s", e)
            data = {"action": action, "tasks": [], "error": str(e)}

        return data

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return f"Tasks: {data['error']}"
        if data.get("action") == "add":
            created = data.get("created", {})
            return f"Task created: {created.get('title', '')}"
        tasks = data.get("tasks", [])
        if not tasks:
            return "No pending tasks."
        lines = [f"Google Tasks ({len(tasks)} pending):"]
        for t in tasks[:10]:
            due = f" (due {t['due'][:10]})" if t.get("due") else ""
            lines.append(f"  - {t['title']}{due}")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "gtasks_list",
                "description": "List pending Google Tasks.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "list"}),
            },
            {
                "name": "gtasks_add",
                "description": "Add a new Google Task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "notes": {"type": "string", "description": "Optional task notes"},
                    },
                    "required": ["title"],
                },
                "handler": lambda title="", notes="", **kw: _sync_fetch(
                    self, {"action": "add", "title": title, "notes": notes}
                ),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
