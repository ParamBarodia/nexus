"""Medium Stats connector stub.

API URL : https://medium.com/@<user>/stats
Auth     : Integration token
Env vars : MEDIUM_INTEGRATION_TOKEN
Category : news
"""

from brain.connectors.base import BaseConnector


class MediumStatsConnector(BaseConnector):
    name = "medium_stats"
    description = "Article views, reads, and follower stats from Medium"
    category = "news"
    required_env = ["MEDIUM_INTEGRATION_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Medium Stats API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
