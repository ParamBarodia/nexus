"""Jira connector stub.

API URL : https://<instance>.atlassian.net/rest/api/3/
Auth     : API key (email + token)
Env vars : JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
Category : dev
"""

from brain.connectors.base import BaseConnector


class JiraConnector(BaseConnector):
    name = "jira"
    description = "Issues, sprints, and project status from Jira"
    category = "dev"
    required_env = ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Jira API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
