"""F1 connector — OpenF1 API (free, no auth)."""

from brain.connectors.base import BaseConnector


class F1OpenF1Connector(BaseConnector):
    name = "f1"
    description = "Formula 1 race schedule and session data from OpenF1"
    category = "sports"
    poll_interval_minutes = 360
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "next_race")
        http = await self._get_http()

        if action == "standings":
            # OpenF1 doesn't have full standings — use sessions as proxy
            resp = await http.get(
                "https://api.openf1.org/v1/sessions",
                params={"year": "2026", "session_type": "Race"},
            )
            resp.raise_for_status()
            sessions = resp.json()
            return {
                "action": "standings",
                "races": [
                    {"name": s.get("meeting_name", ""), "date": s.get("date_start", ""),
                     "circuit": s.get("circuit_short_name", "")}
                    for s in sessions[:20]
                ],
            }
        else:
            # Next/latest session
            resp = await http.get(
                "https://api.openf1.org/v1/sessions",
                params={"year": "2026"},
            )
            resp.raise_for_status()
            sessions = resp.json()
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            upcoming = [s for s in sessions if s.get("date_start", "") >= now]
            if upcoming:
                nxt = upcoming[0]
            elif sessions:
                nxt = sessions[-1]
            else:
                return {"action": "next_race", "race": None}

            return {
                "action": "next_race",
                "race": {
                    "name": nxt.get("meeting_name", ""),
                    "session": nxt.get("session_name", ""),
                    "date": nxt.get("date_start", ""),
                    "circuit": nxt.get("circuit_short_name", ""),
                    "country": nxt.get("country_name", ""),
                },
            }

    def briefing_summary(self, data: dict) -> str:
        if data.get("action") == "next_race" and data.get("race"):
            r = data["race"]
            return f"Next F1: {r['name']} ({r['circuit']}, {r['country']}) — {r['date']}"
        return "No upcoming F1 race info available."

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "f1_next_race",
                "description": "Get the next upcoming F1 race.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync(self, {"action": "next_race"}),
            },
            {
                "name": "f1_standings",
                "description": "Get F1 2026 race calendar.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync(self, {"action": "standings"}),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    if params.get("action") == "next_race":
        r = data.get("race")
        if not r:
            return "No upcoming F1 race found."
        return f"Next F1: {r['name']} at {r['circuit']}, {r['country']} on {r['date']}"
    races = data.get("races", [])
    return "\n".join(f"- {r['name']} ({r['circuit']}) {r['date']}" for r in races) or "No races found."
