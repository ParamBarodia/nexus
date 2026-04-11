"""Spotify connector -- now playing & recent tracks via Spotify Web API.

Uses access token from encrypted credential store or SPOTIFY_ACCESS_TOKEN env var.
If no token is available, returns a helpful setup message instead of failing.
"""

import logging
import os

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.spotify")

API_BASE = "https://api.spotify.com/v1"


class SpotifyPlayerConnector(BaseConnector):
    name = "spotify"
    description = "Currently playing track and recently played from Spotify"
    category = "personal"
    poll_interval_minutes = 0
    required_env = []

    def _get_token(self) -> str | None:
        """Resolve access token — auto-refresh via spotify_auth if available."""
        try:
            from brain.connectors.services.spotify_auth import get_valid_token
            token = get_valid_token()
            if token:
                return token
        except Exception:
            pass
        token = get_credential("spotify", "access_token")
        if not token:
            token = os.getenv("SPOTIFY_ACCESS_TOKEN")
        return token

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "now_playing")
        token = self._get_token()

        if not token:
            return {
                "error": "no_credentials",
                "action": action,
                "message": (
                    "Spotify access token not configured. "
                    "To set up: 1) Create an app at https://developer.spotify.com/dashboard, "
                    "2) Complete OAuth2 flow to get an access token, "
                    "3) Store it via `brain.connectors.auth.store_credential('spotify', 'access_token', '<token>')` "
                    "or set SPOTIFY_ACCESS_TOKEN in .env."
                ),
            }

        http = await self._get_http()
        headers = {"Authorization": f"Bearer {token}"}

        if action == "recent":
            cached = self._cache_get("spotify_recent")
            if cached:
                return cached
            resp = await http.get(
                f"{API_BASE}/me/player/recently-played",
                headers=headers,
                params={"limit": 10},
            )
            if resp.status_code == 401:
                return {"error": "token_expired", "action": action,
                        "message": "Spotify token expired. Please refresh your OAuth token."}
            resp.raise_for_status()
            items = resp.json().get("items", [])
            result = {
                "action": "recent",
                "tracks": [
                    {
                        "name": item["track"]["name"],
                        "artist": ", ".join(a["name"] for a in item["track"]["artists"]),
                        "album": item["track"]["album"]["name"],
                        "played_at": item.get("played_at", ""),
                        "url": item["track"]["external_urls"].get("spotify", ""),
                    }
                    for item in items
                ],
            }
            self._cache_set("spotify_recent", result)
            return result

        else:  # now_playing
            resp = await http.get(
                f"{API_BASE}/me/player/currently-playing",
                headers=headers,
            )
            if resp.status_code == 204:
                return {"action": "now_playing", "playing": False,
                        "message": "Nothing is currently playing on Spotify."}
            if resp.status_code == 401:
                return {"error": "token_expired", "action": action,
                        "message": "Spotify token expired. Please refresh your OAuth token."}
            resp.raise_for_status()
            data = resp.json()
            track = data.get("item", {})
            return {
                "action": "now_playing",
                "playing": data.get("is_playing", False),
                "name": track.get("name", "Unknown"),
                "artist": ", ".join(a["name"] for a in track.get("artists", [])),
                "album": track.get("album", {}).get("name", ""),
                "progress_ms": data.get("progress_ms", 0),
                "duration_ms": track.get("duration_ms", 0),
                "url": track.get("external_urls", {}).get("spotify", ""),
            }

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return data["message"]

        action = data.get("action", "now_playing")

        if action == "recent":
            tracks = data.get("tracks", [])[:5]
            if not tracks:
                return "No recently played Spotify tracks."
            lines = ["Recently played on Spotify:"]
            for t in tracks:
                lines.append(f"  - {t['name']} by {t['artist']}")
            return "\n".join(lines)

        # now_playing
        if not data.get("playing"):
            return data.get("message", "Nothing playing on Spotify.")
        return f"Now playing: {data['name']} by {data['artist']} ({data['album']})"

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "spotify_now_playing",
                "description": "Get the currently playing track on Spotify.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync(self, {"action": "now_playing"}),
            },
            {
                "name": "spotify_recent",
                "description": "Get recently played tracks on Spotify.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync(self, {"action": "recent"}),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
