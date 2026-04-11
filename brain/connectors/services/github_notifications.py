"""GitHub notifications connector — notifications and repos via GitHub API (PAT token)."""

import os
import logging

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.github_notifications")

GITHUB_API = "https://api.github.com"


class GitHubNotificationsConnector(BaseConnector):
    name = "github_notifications"
    description = "GitHub — notifications and repository activity"
    category = "dev"
    poll_interval_minutes = 30
    required_env = ["GITHUB_PAT"]

    def _get_token(self) -> str:
        token = os.getenv("GITHUB_PAT") or get_credential("github", "pat")
        if not token:
            raise RuntimeError(
                "GitHub PAT not configured. "
                "Set GITHUB_PAT env var or store via auth.store_credential('github', 'pat', ...)."
            )
        return token

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "notifications")

        cache_key = f"github_{action}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            token = self._get_token()
        except RuntimeError as e:
            return {"error": str(e), "action": action}

        http = await self._get_http()
        headers = self._headers(token)

        try:
            if action == "repos":
                resp = await http.get(
                    f"{GITHUB_API}/user/repos",
                    headers=headers,
                    params={"sort": "updated", "per_page": 15, "affiliation": "owner,collaborator"},
                )
                resp.raise_for_status()
                repos = []
                for r in resp.json():
                    repos.append({
                        "name": r.get("full_name", ""),
                        "description": (r.get("description") or "")[:100],
                        "language": r.get("language", ""),
                        "stars": r.get("stargazers_count", 0),
                        "updated": r.get("updated_at", ""),
                        "private": r.get("private", False),
                        "url": r.get("html_url", ""),
                    })
                data = {"action": "repos", "repos": repos}
            else:
                # notifications
                resp = await http.get(
                    f"{GITHUB_API}/notifications",
                    headers=headers,
                    params={"all": "false", "per_page": 20},
                )
                resp.raise_for_status()
                notifications = []
                for n in resp.json():
                    notifications.append({
                        "id": n.get("id", ""),
                        "repo": n.get("repository", {}).get("full_name", ""),
                        "type": n.get("subject", {}).get("type", ""),
                        "title": n.get("subject", {}).get("title", ""),
                        "reason": n.get("reason", ""),
                        "updated": n.get("updated_at", ""),
                        "unread": n.get("unread", False),
                    })
                data = {"action": "notifications", "notifications": notifications}

            self._cache_set(cache_key, data)

        except Exception as e:
            logger.error("GitHub API error: %s", e)
            data = {"error": str(e), "action": action}

        return data

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return f"GitHub: {data['error']}"
        if data.get("action") == "repos":
            repos = data.get("repos", [])
            if not repos:
                return "No GitHub repos found."
            lines = ["GitHub Repos (recent):"]
            for r in repos[:8]:
                lang = f" [{r['language']}]" if r.get("language") else ""
                vis = " (private)" if r.get("private") else ""
                lines.append(f"  - {r['name']}{lang}{vis} ({r['stars']} stars)")
            return "\n".join(lines)
        else:
            notifs = data.get("notifications", [])
            if not notifs:
                return "No unread GitHub notifications."
            lines = [f"GitHub Notifications ({len(notifs)}):"]
            for n in notifs[:8]:
                lines.append(f"  - [{n['type']}] {n['repo']}: {n['title']} ({n['reason']})")
            return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "github_notifications",
                "description": "Get unread GitHub notifications.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "notifications"}),
            },
            {
                "name": "github_repos",
                "description": "List recent GitHub repositories.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "repos"}),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
