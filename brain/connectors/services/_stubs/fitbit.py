"""Fitbit connector stub.

API URL : https://api.fitbit.com/1/
Auth     : OAuth2
Env vars : FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET, FITBIT_REFRESH_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class FitbitConnector(BaseConnector):
    name = "fitbit"
    description = "Steps, heart rate, sleep, and activity data from Fitbit"
    category = "personal"
    required_env = ["FITBIT_CLIENT_ID", "FITBIT_CLIENT_SECRET", "FITBIT_REFRESH_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Fitbit API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
