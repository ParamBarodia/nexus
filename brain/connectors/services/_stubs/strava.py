"""Strava connector stub.

API URL : https://www.strava.com/api/v3/
Auth     : OAuth2
Env vars : STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class StravaConnector(BaseConnector):
    name = "strava"
    description = "Activities, routes, and fitness stats from Strava"
    category = "personal"
    required_env = ["STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Strava API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
