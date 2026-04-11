"""Datadog connector stub.

API URL : https://api.datadoghq.com/api/v1/
Auth     : API key + Application key
Env vars : DATADOG_API_KEY, DATADOG_APP_KEY
Category : dev
"""

from brain.connectors.base import BaseConnector


class DatadogConnector(BaseConnector):
    name = "datadog"
    description = "Monitors, alerts, and infrastructure metrics from Datadog"
    category = "dev"
    required_env = ["DATADOG_API_KEY", "DATADOG_APP_KEY"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Datadog API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
