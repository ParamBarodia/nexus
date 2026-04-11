"""Slack connector stub.

API URL : https://api.slack.com/api/
Auth     : OAuth2 (Bot token)
Env vars : SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
Category : personal
"""

from brain.connectors.base import BaseConnector


class SlackConnector(BaseConnector):
    name = "slack"
    description = "Unread messages, channels, and mentions from Slack"
    category = "personal"
    required_env = ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Slack API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
