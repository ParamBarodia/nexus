"""Todoist connector stub.

API URL : https://api.todoist.com/rest/v2/
Auth     : API key
Env vars : TODOIST_API_KEY
Category : personal
"""

from brain.connectors.base import BaseConnector


class TodoistConnector(BaseConnector):
    name = "todoist"
    description = "Tasks, projects, and productivity stats from Todoist"
    category = "personal"
    required_env = ["TODOIST_API_KEY"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Todoist API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
