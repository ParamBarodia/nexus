"""PyPI Stats connector stub.

API URL : https://pypistats.org/api/
Auth     : Free (no auth required)
Env vars : PYPI_PACKAGE_NAMES
Category : dev
"""

from brain.connectors.base import BaseConnector


class PyPIStatsConnector(BaseConnector):
    name = "pypi_stats"
    description = "Download statistics and version info for Python packages on PyPI"
    category = "dev"
    required_env = ["PYPI_PACKAGE_NAMES"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement PyPI Stats API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
