"""Telegram Bot connector stub.

API URL : https://api.telegram.org/bot<token>/
Auth     : Bot token
Env vars : TELEGRAM_BOT_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class TelegramBotConnector(BaseConnector):
    name = "telegram_bot"
    description = "Updates, messages, and chat activity from Telegram"
    category = "personal"
    required_env = ["TELEGRAM_BOT_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Telegram Bot API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
