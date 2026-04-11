"""Sentry connector stub.

API URL : https://sentry.io/api/0/
Auth     : API key (Bearer token)
Env vars : SENTRY_AUTH_TOKEN, SENTRY_ORG_SLUG
Category : dev
"""

from brain.connectors.base import BaseConnector


class SentryConnector(BaseConnector):
    name = "sentry"
    description = "Error counts, unresolved issues, and crash-free rates from Sentry"
    category = "dev"
    required_env = ["SENTRY_AUTH_TOKEN", "SENTRY_ORG_SLUG"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Sentry API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
