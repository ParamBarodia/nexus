"""Twitch connector stub.

API URL : https://api.twitch.tv/helix/
Auth     : OAuth2
Env vars : TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, TWITCH_OAUTH_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class TwitchConnector(BaseConnector):
    name = "twitch"
    description = "Followed streams, live status, and chat activity from Twitch"
    category = "personal"
    required_env = ["TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "TWITCH_OAUTH_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Twitch API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
