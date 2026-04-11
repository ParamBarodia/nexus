"""Social notifications connector -- Instagram/Twitter activity via browser history.

Since Instagram and Twitter/X APIs require business accounts or paid access,
this connector takes a practical approach: it reads the local browser history
(Chrome or Edge SQLite database) to detect recent social-media activity.
No API keys required.
"""

import logging
import os
import platform
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from brain.connectors.base import BaseConnector

logger = logging.getLogger("jarvis.connectors.social_notifs")

# Social media domains to track
SOCIAL_DOMAINS = [
    "instagram.com",
    "twitter.com",
    "x.com",
]

# Chrome epoch starts at 1601-01-01 (Windows FILETIME-like)
CHROME_EPOCH_OFFSET = 11644473600


def _chrome_timestamp_to_datetime(chrome_ts: int) -> datetime:
    """Convert Chrome/Edge microsecond timestamp to Python datetime."""
    if chrome_ts == 0:
        return datetime.min
    # Chrome stores timestamps as microseconds since 1601-01-01
    unix_ts = (chrome_ts / 1_000_000) - CHROME_EPOCH_OFFSET
    try:
        return datetime.fromtimestamp(unix_ts)
    except (OSError, ValueError):
        return datetime.min


def _find_browser_history_paths() -> list[Path]:
    """Locate Chrome and Edge History SQLite databases."""
    paths = []

    if platform.system() == "Windows":
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            # Chrome
            chrome_path = Path(local_app) / "Google" / "Chrome" / "User Data" / "Default" / "History"
            if chrome_path.exists():
                paths.append(chrome_path)

            # Edge
            edge_path = Path(local_app) / "Microsoft" / "Edge" / "User Data" / "Default" / "History"
            if edge_path.exists():
                paths.append(edge_path)
    elif platform.system() == "Darwin":
        home = Path.home()
        chrome_path = home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "History"
        if chrome_path.exists():
            paths.append(chrome_path)
    else:  # Linux
        home = Path.home()
        chrome_path = home / ".config" / "google-chrome" / "Default" / "History"
        if chrome_path.exists():
            paths.append(chrome_path)
        edge_path = home / ".config" / "microsoft-edge" / "Default" / "History"
        if edge_path.exists():
            paths.append(edge_path)

    return paths


def _query_browser_history(hours_back: int = 24) -> list[dict]:
    """Read social media URLs from browser history.

    The browser locks its History file, so we copy it to a temp location first.
    """
    history_paths = _find_browser_history_paths()
    if not history_paths:
        return []

    cutoff = datetime.now() - timedelta(hours=hours_back)
    # Chrome timestamp for cutoff
    cutoff_chrome = int((cutoff.timestamp() + CHROME_EPOCH_OFFSET) * 1_000_000)

    all_entries = []

    for hist_path in history_paths:
        tmp_path = None
        try:
            # Copy the locked database to a temp file
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".sqlite")
            os.close(tmp_fd)
            shutil.copy2(str(hist_path), tmp_path)

            conn = sqlite3.connect(tmp_path)
            conn.row_factory = sqlite3.Row

            # Build domain filter
            domain_clauses = " OR ".join(f"url LIKE '%{d}%'" for d in SOCIAL_DOMAINS)

            query = f"""
                SELECT url, title, last_visit_time, visit_count
                FROM urls
                WHERE ({domain_clauses})
                  AND last_visit_time > ?
                ORDER BY last_visit_time DESC
                LIMIT 50
            """
            cursor = conn.execute(query, (cutoff_chrome,))
            rows = cursor.fetchall()

            browser_name = "Chrome" if "Chrome" in str(hist_path) else "Edge"
            for row in rows:
                visited_at = _chrome_timestamp_to_datetime(row["last_visit_time"])
                url = row["url"]
                # Determine platform
                plat = "unknown"
                for domain in SOCIAL_DOMAINS:
                    if domain in url:
                        plat = domain.replace(".com", "").replace(".", "")
                        break

                all_entries.append({
                    "platform": plat,
                    "url": url,
                    "title": row["title"] or "",
                    "visited_at": visited_at.isoformat(),
                    "visit_count": row["visit_count"],
                    "browser": browser_name,
                })

            conn.close()
        except Exception as e:
            logger.warning("Failed to read browser history from %s: %s", hist_path, e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # Deduplicate by URL, keep most recent
    seen = {}
    for entry in all_entries:
        key = entry["url"]
        if key not in seen or entry["visited_at"] > seen[key]["visited_at"]:
            seen[key] = entry

    results = sorted(seen.values(), key=lambda e: e["visited_at"], reverse=True)
    return results


class SocialNotificationsConnector(BaseConnector):
    name = "social_notifs"
    description = "Instagram/Twitter activity detection via browser history (no API keys needed)"
    category = "personal"
    poll_interval_minutes = 60
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        hours = params.get("hours", 24)

        cached = self._cache_get(f"social_check_{hours}")
        if cached:
            return cached

        entries = _query_browser_history(hours_back=hours)

        # Group by platform
        by_platform = {}
        for entry in entries:
            plat = entry["platform"]
            if plat not in by_platform:
                by_platform[plat] = []
            by_platform[plat].append(entry)

        result = {
            "action": "check",
            "hours_back": hours,
            "total_visits": len(entries),
            "by_platform": {
                plat: {
                    "count": len(items),
                    "recent": items[:5],
                }
                for plat, items in by_platform.items()
            },
            "recent_entries": entries[:10],
        }

        self._cache_set(f"social_check_{hours}", result)
        return result

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return data.get("message", "Social notifications check failed.")

        total = data.get("total_visits", 0)
        hours = data.get("hours_back", 24)

        if total == 0:
            return f"No social media activity detected in browser history (last {hours}h)."

        lines = [f"Social media activity in the last {hours}h ({total} page visits):"]
        by_platform = data.get("by_platform", {})
        for plat, info in by_platform.items():
            count = info["count"]
            recent = info.get("recent", [])
            display_name = {"instagram": "Instagram", "twitter": "Twitter",
                            "x": "X/Twitter"}.get(plat, plat.title())
            lines.append(f"  {display_name}: {count} visits")
            for entry in recent[:2]:
                title = entry.get("title", "")[:60]
                if title:
                    lines.append(f"    - {title}")

        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "social_check",
                "description": "Check recent social media (Instagram/Twitter) activity from browser history.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hours": {
                            "type": "integer",
                            "description": "How many hours back to check (default: 24)",
                            "default": 24,
                        },
                    },
                },
                "handler": lambda hours=24, **kw: _sync(self, {"hours": hours}),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
