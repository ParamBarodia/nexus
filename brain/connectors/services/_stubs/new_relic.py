"""New Relic connector stub.

API URL : https://api.newrelic.com/v2/
Auth     : API key
Env vars : NEW_RELIC_API_KEY, NEW_RELIC_ACCOUNT_ID
Category : dev
"""

from brain.connectors.base import BaseConnector


class NewRelicConnector(BaseConnector):
    name = "new_relic"
    description = "APM data, error rates, and throughput from New Relic"
    category = "dev"
    required_env = ["NEW_RELIC_API_KEY", "NEW_RELIC_ACCOUNT_ID"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement New Relic API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
