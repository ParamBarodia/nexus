"""Steam connector stub.

API URL : https://api.steampowered.com/
Auth     : API key
Env vars : STEAM_API_KEY, STEAM_USER_ID
Category : personal
"""

from brain.connectors.base import BaseConnector


class SteamConnector(BaseConnector):
    name = "steam"
    description = "Game library, playtime, and friend activity from Steam"
    category = "personal"
    required_env = ["STEAM_API_KEY", "STEAM_USER_ID"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Steam API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
