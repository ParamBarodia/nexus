"""UptimeRobot connector stub.

API URL : https://api.uptimerobot.com/v2/
Auth     : API key
Env vars : UPTIMEROBOT_API_KEY
Category : dev
"""

from brain.connectors.base import BaseConnector


class UptimeRobotConnector(BaseConnector):
    name = "uptime_robot"
    description = "Monitor status, uptime percentages, and alerts from UptimeRobot"
    category = "dev"
    required_env = ["UPTIMEROBOT_API_KEY"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement UptimeRobot API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
