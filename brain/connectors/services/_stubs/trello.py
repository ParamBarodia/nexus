"""Trello connector stub.

API URL : https://api.trello.com/1/
Auth     : API key + token
Env vars : TRELLO_API_KEY, TRELLO_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class TrelloConnector(BaseConnector):
    name = "trello"
    description = "Boards, lists, and cards from Trello"
    category = "personal"
    required_env = ["TRELLO_API_KEY", "TRELLO_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Trello API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
