"""Reddit watchlist connector — uses reddit.com/.json (free, no auth)."""

import os

from brain.connectors.base import BaseConnector


class RedditWatchlistConnector(BaseConnector):
    name = "reddit"
    description = "Top posts from watched subreddits"
    category = "news"
    poll_interval_minutes = 60
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        subs_str = params.get("subreddits") or os.getenv("REDDIT_SUBS", "LocalLLaMA,neuroscience,india")
        subs = [s.strip() for s in subs_str.split(",") if s.strip()]
        limit = int(params.get("limit", 5))

        http = await self._get_http()
        all_posts = []

        for sub in subs:
            cache_key = f"reddit_{sub}"
            cached = self._cache_get(cache_key)
            if cached:
                all_posts.extend(cached)
                continue

            try:
                resp = await http.get(
                    f"https://www.reddit.com/r/{sub}/hot.json",
                    params={"limit": limit},
                    headers={"User-Agent": "NexusBot/1.0"},
                )
                resp.raise_for_status()
                children = resp.json().get("data", {}).get("children", [])
                posts = []
                for c in children:
                    d = c.get("data", {})
                    posts.append({
                        "title": d.get("title", ""),
                        "score": d.get("score", 0),
                        "url": f"https://reddit.com{d.get('permalink', '')}",
                        "subreddit": sub,
                        "comments": d.get("num_comments", 0),
                    })
                self._cache_set(cache_key, posts)
                all_posts.extend(posts)
            except Exception as e:
                all_posts.append({"title": f"[Error fetching r/{sub}: {e}]", "score": 0, "subreddit": sub, "url": "", "comments": 0})

        all_posts.sort(key=lambda p: p.get("score", 0), reverse=True)
        return {"subreddits": subs, "posts": all_posts}

    def briefing_summary(self, data: dict) -> str:
        posts = data.get("posts", [])[:5]
        if not posts:
            return "No Reddit posts available."
        lines = ["Reddit hot:"]
        for p in posts:
            lines.append(f"  - r/{p['subreddit']}: {p['title']} ({p['score']} pts)")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "reddit_top",
                "description": "Get top posts from watched subreddits. Optional: subreddits (comma-separated).",
                "parameters": {
                    "type": "object",
                    "properties": {"subreddits": {"type": "string", "description": "Comma-separated subreddit names"}},
                },
                "handler": lambda subreddits=None, **kw: _sync(self, subreddits),
            }
        ]


def _sync(connector, subreddits=None):
    import asyncio
    params = {}
    if subreddits:
        params["subreddits"] = subreddits
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
