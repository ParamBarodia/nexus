"""Home Assistant connector stub.

API URL : http://<local-instance>:8123/api/
Auth     : Long-lived access token
Env vars : HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN
Category : environmental
"""

from brain.connectors.base import BaseConnector


class HomeAssistantConnector(BaseConnector):
    name = "home_assistant"
    description = "Smart home device states, automations, and sensor data from Home Assistant"
    category = "environmental"
    required_env = ["HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Home Assistant API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
