"""NPM Downloads connector stub.

API URL : https://api.npmjs.org/downloads/
Auth     : Free (no auth required)
Env vars : NPM_PACKAGE_NAMES
Category : dev
"""

from brain.connectors.base import BaseConnector


class NPMDownloadsConnector(BaseConnector):
    name = "npm_downloads"
    description = "Daily and weekly download counts for NPM packages"
    category = "dev"
    required_env = ["NPM_PACKAGE_NAMES"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement NPM Downloads API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
