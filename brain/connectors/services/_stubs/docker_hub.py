"""Docker Hub connector stub.

API URL : https://hub.docker.com/v2/
Auth     : Free (no auth required for public data)
Env vars : DOCKER_HUB_USERNAME
Category : dev
"""

from brain.connectors.base import BaseConnector


class DockerHubConnector(BaseConnector):
    name = "docker_hub"
    description = "Repository info, image tags, and pull counts from Docker Hub"
    category = "dev"
    required_env = ["DOCKER_HUB_USERNAME"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Docker Hub API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
