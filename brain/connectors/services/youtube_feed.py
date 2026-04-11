"""YouTube connector -- trending videos via free RSS feeds (no API key required).

Can optionally use the YouTube Data API v3 if YOUTUBE_API_KEY is set,
but the default path uses YouTube RSS feeds parsed with feedparser.
"""

import logging
import os
import xml.etree.ElementTree as ET

from brain.connectors.base import BaseConnector

logger = logging.getLogger("jarvis.connectors.youtube")

# YouTube RSS feed for a channel:
# https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
#
# For trending, we use well-known aggregator/trending channels
# and the YouTube Data API when available.

API_BASE = "https://youtube.googleapis.com/youtube/v3"

# Popular Indian YouTube channels to aggregate a "trending" feel via RSS
TRENDING_CHANNELS_IN = [
    "UCq-Fj5jknLsUf-MWSy4_brA",  # T-Series
    "UCp-jGkjLzNCA9gxCPGpcjRQ",  # SET India
    "UCk1SpWNzOs4MYmr0uICEntg",  # Zee Music Company
    "UC0RhatS1pyxInC00YKjjBqQ",  # Goldmines
    "UCVHFbqXqoYvEWM1Ddxl0QDg",  # ABP News
]


class YouTubeFeedConnector(BaseConnector):
    name = "youtube"
    description = "YouTube trending and channel feeds via RSS (free, no API key needed)"
    category = "personal"
    poll_interval_minutes = 0
    required_env = []

    async def _fetch_rss_feed(self, channel_id: str) -> list[dict]:
        """Parse a YouTube channel RSS feed and return video entries."""
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        http = await self._get_http()
        try:
            resp = await http.get(url)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to fetch RSS for channel %s: %s", channel_id, e)
            return []

        videos = []
        try:
            root = ET.fromstring(resp.text)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "media": "http://search.yahoo.com/mrss/",
            }
            for entry in root.findall("atom:entry", ns)[:5]:
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                published_el = entry.find("atom:published", ns)
                author_el = entry.find("atom:author/atom:name", ns)
                media_group = entry.find("media:group", ns)
                description = ""
                if media_group is not None:
                    desc_el = media_group.find("media:description", ns)
                    if desc_el is not None and desc_el.text:
                        description = desc_el.text[:200]

                videos.append({
                    "title": title_el.text if title_el is not None else "Untitled",
                    "url": link_el.get("href", "") if link_el is not None else "",
                    "published": published_el.text if published_el is not None else "",
                    "channel": author_el.text if author_el is not None else "",
                    "description": description,
                })
        except ET.ParseError as e:
            logger.warning("RSS parse error for channel %s: %s", channel_id, e)

        return videos

    async def _fetch_trending_api(self, region: str = "IN") -> list[dict]:
        """Fetch trending videos via YouTube Data API v3 (requires key)."""
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return []

        http = await self._get_http()
        resp = await http.get(
            f"{API_BASE}/videos",
            params={
                "part": "snippet",
                "chart": "mostPopular",
                "regionCode": region,
                "maxResults": 15,
                "key": api_key,
            },
        )
        if resp.status_code != 200:
            logger.warning("YouTube API error %s: %s", resp.status_code, resp.text[:200])
            return []

        items = resp.json().get("items", [])
        return [
            {
                "title": item["snippet"]["title"],
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "published": item["snippet"]["publishedAt"],
                "channel": item["snippet"]["channelTitle"],
                "description": item["snippet"].get("description", "")[:200],
            }
            for item in items
        ]

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "trending")
        region = params.get("region", "IN")
        channel_id = params.get("channel_id")

        if action == "channel" and channel_id:
            cached = self._cache_get(f"yt_channel_{channel_id}")
            if cached:
                return cached
            videos = await self._fetch_rss_feed(channel_id)
            result = {"action": "channel", "channel_id": channel_id, "videos": videos}
            self._cache_set(f"yt_channel_{channel_id}", result)
            return result

        # trending
        cached = self._cache_get(f"yt_trending_{region}")
        if cached:
            return cached

        # Try API first if key is available
        videos = await self._fetch_trending_api(region)

        if not videos:
            # Free fallback: aggregate RSS feeds from popular channels
            all_videos = []
            for cid in TRENDING_CHANNELS_IN:
                feed_videos = await self._fetch_rss_feed(cid)
                all_videos.extend(feed_videos)

            # Sort by published date (newest first) and deduplicate
            all_videos.sort(key=lambda v: v.get("published", ""), reverse=True)
            videos = all_videos[:15]

        result = {"action": "trending", "region": region, "videos": videos}
        self._cache_set(f"yt_trending_{region}", result)
        return result

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return data.get("message", "YouTube fetch error.")

        videos = data.get("videos", [])[:5]
        if not videos:
            return "No YouTube videos found."

        action = data.get("action", "trending")
        if action == "channel":
            header = f"Latest from YouTube channel:"
        else:
            header = f"Trending on YouTube ({data.get('region', 'IN')}):"

        lines = [header]
        for v in videos:
            channel = f" [{v['channel']}]" if v.get("channel") else ""
            lines.append(f"  - {v['title']}{channel}")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "youtube_trending",
                "description": "Get trending YouTube videos in India (via RSS feeds or API).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "region": {
                            "type": "string",
                            "description": "ISO region code (default: IN)",
                            "default": "IN",
                        },
                    },
                },
                "handler": lambda region="IN", **kw: _sync(
                    self, {"action": "trending", "region": region}
                ),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
