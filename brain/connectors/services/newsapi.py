"""NewsAPI connector — top headlines and search via NewsAPI.org."""

import os
import logging

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.newsapi")

NEWSAPI_BASE = "https://newsapi.org/v2"


class NewsAPIConnector(BaseConnector):
    name = "newsapi"
    description = "NewsAPI.org — top headlines and article search"
    category = "news"
    poll_interval_minutes = 60
    required_env = ["NEWSAPI_KEY"]

    def _get_api_key(self) -> str:
        key = os.getenv("NEWSAPI_KEY") or get_credential("newsapi", "api_key")
        if not key:
            raise RuntimeError(
                "NewsAPI key not configured. "
                "Set NEWSAPI_KEY env var or store via auth.store_credential('newsapi', 'api_key', ...)."
            )
        return key

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "headlines")
        country = params.get("country", os.getenv("NEWS_COUNTRY", "in"))
        category = params.get("category", "")

        cache_key = f"newsapi_{action}_{country}_{category}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            api_key = self._get_api_key()
        except RuntimeError as e:
            return {"error": str(e), "action": action, "articles": []}

        http = await self._get_http()

        try:
            if action == "search":
                query = params.get("query", "")
                if not query:
                    return {"error": "Search query required", "action": "search", "articles": []}
                resp = await http.get(
                    f"{NEWSAPI_BASE}/everything",
                    params={"q": query, "pageSize": 10, "sortBy": "publishedAt", "apiKey": api_key},
                )
            else:
                # headlines
                req_params = {"country": country, "pageSize": 10, "apiKey": api_key}
                if category:
                    req_params["category"] = category
                resp = await http.get(f"{NEWSAPI_BASE}/top-headlines", params=req_params)

            resp.raise_for_status()
            raw = resp.json()

            if raw.get("status") != "ok":
                return {"error": raw.get("message", "NewsAPI error"), "action": action, "articles": []}

            articles = []
            for a in raw.get("articles", []):
                articles.append({
                    "title": a.get("title", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "description": (a.get("description") or "")[:150],
                    "url": a.get("url", ""),
                    "published": a.get("publishedAt", ""),
                })
            data = {"action": action, "articles": articles, "total": raw.get("totalResults", 0)}
            self._cache_set(cache_key, data)

        except Exception as e:
            logger.error("NewsAPI error: %s", e)
            data = {"error": str(e), "action": action, "articles": []}

        return data

    def briefing_summary(self, data: dict) -> str:
        articles = data.get("articles", [])
        if data.get("error"):
            return f"News: {data['error']}"
        if not articles:
            return "No news articles available."
        lines = [f"News Headlines ({len(articles)} articles):"]
        for a in articles[:8]:
            source = f" ({a['source']})" if a.get("source") else ""
            lines.append(f"  - {a['title']}{source}")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "news_headlines",
                "description": "Get top news headlines.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "country": {"type": "string", "description": "Country code (default: in)"},
                        "category": {"type": "string", "description": "Category: business, tech, sports, etc."},
                    },
                },
                "handler": lambda country="", category="", **kw: _sync_fetch(
                    self, {
                        "action": "headlines",
                        **({"country": country} if country else {}),
                        **({"category": category} if category else {}),
                    }
                ),
            },
            {
                "name": "news_search",
                "description": "Search news articles by keyword.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query"}},
                    "required": ["query"],
                },
                "handler": lambda query="", **kw: _sync_fetch(self, {"action": "search", "query": query}),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
