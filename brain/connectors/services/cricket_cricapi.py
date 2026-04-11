"""Cricket connector — live scores and schedule via CricAPI.com."""

import os
import logging

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.cricket_cricapi")

CRICAPI_BASE = "https://api.cricapi.com/v1"


class CricketCricAPIConnector(BaseConnector):
    name = "cricket_cricapi"
    description = "Cricket — live scores and schedule from CricAPI"
    category = "sports"
    poll_interval_minutes = 15
    required_env = ["CRICAPI_KEY"]

    def _get_api_key(self) -> str:
        key = os.getenv("CRICAPI_KEY") or get_credential("cricapi", "api_key")
        if not key:
            raise RuntimeError(
                "CricAPI key not configured. "
                "Set CRICAPI_KEY env var or store via auth.store_credential('cricapi', 'api_key', ...)."
            )
        return key

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "live")

        cache_key = f"cricket_{action}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            api_key = self._get_api_key()
        except RuntimeError as e:
            return {"error": str(e), "action": action, "matches": []}

        http = await self._get_http()

        try:
            if action == "schedule":
                resp = await http.get(
                    f"{CRICAPI_BASE}/matches",
                    params={"apikey": api_key, "offset": 0},
                )
            else:
                # live / current matches
                resp = await http.get(
                    f"{CRICAPI_BASE}/currentMatches",
                    params={"apikey": api_key, "offset": 0},
                )

            resp.raise_for_status()
            raw = resp.json()

            if raw.get("status") != "success":
                return {"error": raw.get("reason", "CricAPI error"), "action": action, "matches": []}

            matches = []
            for m in raw.get("data", [])[:15]:
                match_info = {
                    "name": m.get("name", ""),
                    "status": m.get("status", ""),
                    "venue": m.get("venue", ""),
                    "date": m.get("date", ""),
                    "match_type": m.get("matchType", ""),
                }
                # Add score info for live matches
                if m.get("score"):
                    scores = []
                    for s in m["score"]:
                        scores.append(f"{s.get('inning', '')}: {s.get('r', 0)}/{s.get('w', 0)} ({s.get('o', 0)} ov)")
                    match_info["scores"] = scores
                matches.append(match_info)

            data = {"action": action, "matches": matches}
            self._cache_set(cache_key, data)

        except Exception as e:
            logger.error("CricAPI error: %s", e)
            data = {"error": str(e), "action": action, "matches": []}

        return data

    def briefing_summary(self, data: dict) -> str:
        matches = data.get("matches", [])
        if data.get("error"):
            return f"Cricket: {data['error']}"
        if not matches:
            return "No cricket matches available."
        action = data.get("action", "live")
        label = "Live Cricket" if action == "live" else "Cricket Schedule"
        lines = [f"{label}:"]
        for m in matches[:6]:
            line = f"  - {m['name']}"
            if m.get("status"):
                line += f" — {m['status']}"
            if m.get("scores"):
                line += " | " + " ; ".join(m["scores"])
            lines.append(line)
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "cricket_live",
                "description": "Get live cricket scores.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "live"}),
            },
            {
                "name": "cricket_schedule",
                "description": "Get upcoming cricket match schedule.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "schedule"}),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
