"""Azure Status connector stub.

API URL : https://status.azure.com/en-us/status
Auth     : Free (no auth required)
Env vars : (none)
Category : dev
"""

from brain.connectors.base import BaseConnector


class AzureStatusConnector(BaseConnector):
    name = "azure_status"
    description = "Azure service health, incidents, and planned maintenance"
    category = "dev"
    required_env = []

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Azure Status API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
