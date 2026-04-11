"""RSS feed aggregator connector — uses feedparser (free, no auth)."""

import json
import logging
from pathlib import Path

import feedparser

from brain.connectors.base import BaseConnector

logger = logging.getLogger("jarvis.connectors.rss")

FEEDS_FILE = Path(r"C:\jarvis\data\rss_feeds.json")


def _load_feeds() -> list[str]:
    if not FEEDS_FILE.exists():
        return []
    try:
        return json.loads(FEEDS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_feeds(feeds: list[str]):
    FEEDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEEDS_FILE.write_text(json.dumps(feeds, indent=2), encoding="utf-8")


class RSSAggregatorConnector(BaseConnector):
    name = "rss"
    description = "RSS feed aggregator — subscribe to any RSS/Atom feed"
    category = "news"
    poll_interval_minutes = 60
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "latest")

        if action == "add_feed":
            url = params.get("url", "")
            if url:
                feeds = _load_feeds()
                if url not in feeds:
                    feeds.append(url)
                    _save_feeds(feeds)
                return {"action": "add_feed", "url": url, "total_feeds": len(feeds)}
            return {"action": "add_feed", "error": "No URL provided"}

        feeds = _load_feeds()
        if not feeds:
            return {"action": "latest", "articles": [], "message": "No feeds configured. Use rss_add_feed to add one."}

        articles = []
        for feed_url in feeds:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:5]:
                    articles.append({
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": parsed.feed.get("title", feed_url),
                    })
            except Exception as e:
                logger.warning("Failed to parse RSS feed %s: %s", feed_url, e)

        # Sort by published date (best-effort)
        articles.sort(key=lambda a: a.get("published", ""), reverse=True)
        return {"action": "latest", "articles": articles[:20]}

    def briefing_summary(self, data: dict) -> str:
        articles = data.get("articles", [])[:5]
        if not articles:
            return "No RSS articles available."
        lines = ["RSS Headlines:"]
        for a in articles:
            lines.append(f"  - [{a['source']}] {a['title']}")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "rss_latest",
                "description": "Get latest articles from subscribed RSS feeds.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync(self, {"action": "latest"}),
            },
            {
                "name": "rss_add_feed",
                "description": "Subscribe to an RSS feed URL.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string", "description": "RSS feed URL"}},
                    "required": ["url"],
                },
                "handler": lambda url="", **kw: _sync(self, {"action": "add_feed", "url": url}),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    if params.get("action") == "add_feed":
        if "error" in data:
            return data["error"]
        return f"Feed added. Total feeds: {data['total_feeds']}"
    return connector.briefing_summary(data)
