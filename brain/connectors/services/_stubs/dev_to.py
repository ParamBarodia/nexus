"""DEV.to connector stub.

API URL : https://dev.to/api/
Auth     : API key
Env vars : DEVTO_API_KEY
Category : news
"""

from brain.connectors.base import BaseConnector


class DevToConnector(BaseConnector):
    name = "dev_to"
    description = "Articles, comments, and follower stats from DEV.to"
    category = "news"
    required_env = ["DEVTO_API_KEY"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement DEV.to API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
