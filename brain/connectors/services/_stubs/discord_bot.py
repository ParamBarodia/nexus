"""Discord Bot connector stub.

API URL : https://discord.com/api/v10/
Auth     : Bot token
Env vars : DISCORD_BOT_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class DiscordBotConnector(BaseConnector):
    name = "discord_bot"
    description = "Server activity, messages, and notifications from Discord"
    category = "personal"
    required_env = ["DISCORD_BOT_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Discord Bot API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
