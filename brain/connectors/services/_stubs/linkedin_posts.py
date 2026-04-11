"""LinkedIn Posts connector stub.

API URL : https://api.linkedin.com/v2/
Auth     : OAuth2
Env vars : LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_ACCESS_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class LinkedInPostsConnector(BaseConnector):
    name = "linkedin_posts"
    description = "Post engagement, impressions, and network updates from LinkedIn"
    category = "personal"
    required_env = ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_ACCESS_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement LinkedIn Posts API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
