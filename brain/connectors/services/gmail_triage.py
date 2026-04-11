"""Gmail triage connector — unread emails and search via Gmail API (OAuth2 shared with Google)."""

import os
import logging

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.gmail_triage")


class GmailTriageConnector(BaseConnector):
    name = "gmail_triage"
    description = "Gmail — unread inbox triage and email search"
    category = "personal"
    poll_interval_minutes = 15
    required_env = []

    def _get_service(self):
        """Build the Gmail API service using stored OAuth2 credentials."""
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
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        return build("gmail", "v1", credentials=creds)

    def _parse_message(self, service, msg_id: str) -> dict:
        """Fetch and parse a single message's headers."""
        msg = service.users().messages().get(userId="me", id=msg_id, format="metadata",
                                              metadataHeaders=["From", "Subject", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return {
            "id": msg_id,
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", "(No subject)"),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        }

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "unread")

        cached = self._cache_get(f"gmail_{action}")
        if cached:
            return cached

        try:
            service = self._get_service()
        except RuntimeError as e:
            return {"error": str(e), "action": action, "messages": []}

        try:
            if action == "search":
                query = params.get("query", "")
                result = service.users().messages().list(
                    userId="me", q=query, maxResults=10
                ).execute()
            else:
                # unread
                result = service.users().messages().list(
                    userId="me", q="is:unread category:primary", maxResults=15
                ).execute()

            messages = []
            for msg in result.get("messages", [])[:10]:
                try:
                    messages.append(self._parse_message(service, msg["id"]))
                except Exception:
                    continue

            data = {"action": action, "messages": messages, "total": result.get("resultSizeEstimate", 0)}
        except Exception as e:
            logger.error("Gmail API error: %s", e)
            data = {"action": action, "messages": [], "error": str(e)}

        self._cache_set(f"gmail_{action}", data)
        return data

    def briefing_summary(self, data: dict) -> str:
        messages = data.get("messages", [])
        if data.get("error"):
            return f"Gmail: {data['error']}"
        if not messages:
            return "No unread emails in primary inbox."
        lines = [f"Gmail ({data.get('total', len(messages))} messages):"]
        for m in messages[:8]:
            sender = m["from"].split("<")[0].strip() if "<" in m["from"] else m["from"]
            lines.append(f"  - {sender}: {m['subject']}")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "gmail_unread",
                "description": "Get unread emails from primary Gmail inbox.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "unread"}),
            },
            {
                "name": "gmail_search",
                "description": "Search Gmail messages.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Gmail search query"}},
                    "required": ["query"],
                },
                "handler": lambda query="", **kw: _sync_fetch(self, {"action": "search", "query": query}),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
