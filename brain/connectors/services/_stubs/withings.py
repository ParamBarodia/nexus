"""Withings connector stub.

API URL : https://wbsapi.withings.net/
Auth     : OAuth2
Env vars : WITHINGS_CLIENT_ID, WITHINGS_CLIENT_SECRET, WITHINGS_REFRESH_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class WithingsConnector(BaseConnector):
    name = "withings"
    description = "Weight, blood pressure, and health metrics from Withings"
    category = "personal"
    required_env = ["WITHINGS_CLIENT_ID", "WITHINGS_CLIENT_SECRET", "WITHINGS_REFRESH_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Withings API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
