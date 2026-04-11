"""YouTube connector stub.

API URL : https://www.googleapis.com/youtube/v3/
Auth     : OAuth2
Env vars : YOUTUBE_API_KEY, YOUTUBE_OAUTH_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class YouTubeConnector(BaseConnector):
    name = "youtube"
    description = "YouTube subscriptions, watch history, and channel analytics"
    category = "personal"
    required_env = ["YOUTUBE_API_KEY", "YOUTUBE_OAUTH_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement YouTube API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
