"""Hacker News connector — top stories and search via HN Algolia API (free, no auth)."""

from brain.connectors.base import BaseConnector


class HackerNewsConnector(BaseConnector):
    name = "hackernews"
    description = "Hacker News top stories and search via Algolia API"
    category = "news"
    poll_interval_minutes = 60
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "top")
        http = await self._get_http()

        if action == "search":
            query = params.get("query", "AI")
            resp = await http.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": query, "tags": "story", "hitsPerPage": 10},
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            return {
                "action": "search",
                "query": query,
                "stories": [
                    {"title": h.get("title", ""), "url": h.get("url", ""),
                     "points": h.get("points", 0), "author": h.get("author", "")}
                    for h in hits
                ],
            }
        else:
            # Top stories
            resp = await http.get(
                "https://hn.algolia.com/api/v1/search",
                params={"tags": "front_page", "hitsPerPage": 10},
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            return {
                "action": "top",
                "stories": [
                    {"title": h.get("title", ""), "url": h.get("url", ""),
                     "points": h.get("points", 0), "author": h.get("author", "")}
                    for h in hits
                ],
            }

    def briefing_summary(self, data: dict) -> str:
        stories = data.get("stories", [])[:5]
        if not stories:
            return "No Hacker News stories available."
        lines = ["Top Hacker News:"]
        for s in stories:
            lines.append(f"  - {s['title']} ({s['points']} pts)")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "hackernews_top",
                "description": "Get top 10 Hacker News stories.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "top"}),
            },
            {
                "name": "hackernews_search",
                "description": "Search Hacker News stories.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query"}},
                    "required": ["query"],
                },
                "handler": lambda query="AI", **kw: _sync_fetch(self, {"action": "search", "query": query}),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return loop.run_in_executor(pool, lambda: asyncio.run(connector.fetch(params)))
    except RuntimeError:
        data = asyncio.run(connector.fetch(params))
    stories = data.get("stories", [])
    return "\n".join(f"- {s['title']} ({s['points']} pts) {s.get('url', '')}" for s in stories) or "No results."
