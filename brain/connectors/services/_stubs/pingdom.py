"""Pingdom connector stub.

API URL : https://api.pingdom.com/api/3.1/
Auth     : API key
Env vars : PINGDOM_API_KEY
Category : dev
"""

from brain.connectors.base import BaseConnector


class PingdomConnector(BaseConnector):
    name = "pingdom"
    description = "Uptime checks, response times, and outage alerts from Pingdom"
    category = "dev"
    required_env = ["PINGDOM_API_KEY"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Pingdom API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
