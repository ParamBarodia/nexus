"""OpenAI Usage connector stub.

API URL : https://api.openai.com/v1/
Auth     : API key
Env vars : OPENAI_API_KEY
Category : dev
"""

from brain.connectors.base import BaseConnector


class OpenAIUsageConnector(BaseConnector):
    name = "openai_usage"
    description = "API usage, costs, and rate-limit status from OpenAI"
    category = "dev"
    required_env = ["OPENAI_API_KEY"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement OpenAI Usage API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
