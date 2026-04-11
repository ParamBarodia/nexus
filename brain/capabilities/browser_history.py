"""Read recent browser history from Chrome or Edge SQLite databases."""

import json
import os
import shutil
import sqlite3
import tempfile


# Common Windows paths for browser history databases
_HISTORY_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\History"),
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\History"),
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Profile 1\History"),
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Profile 1\History"),
    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\History"),
]


def _browser_history(limit: int = 25, browser: str = "") -> str:
    """Return recent browser history entries.

    Args:
        limit: Maximum number of entries to return (default 25).
        browser: Filter to a specific browser name (chrome, edge, brave). Empty = first found.
    """
    limit = int(limit) if limit else 25

    candidates = _HISTORY_PATHS
    if browser:
        bl = browser.lower()
        candidates = [p for p in candidates if bl in p.lower()]

    for db_path in candidates:
        if not os.path.isfile(db_path):
            continue

        # The History file is locked while the browser runs.
        # Copy to a temp file to avoid locking issues.
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
            tmp.close()
            shutil.copy2(db_path, tmp.name)

            conn = sqlite3.connect(tmp.name)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            os.unlink(tmp.name)

            if not rows:
                continue

            entries = []
            for url, title, ts in rows:
                entries.append({"url": url, "title": title or ""})

            source = "unknown"
            if "chrome" in db_path.lower():
                source = "Chrome"
            elif "edge" in db_path.lower():
                source = "Edge"
            elif "brave" in db_path.lower():
                source = "Brave"

            return json.dumps({"browser": source, "count": len(entries), "entries": entries}, indent=2)
        except Exception as e:
            # Try the next candidate
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            continue

    return "No browser history database found or all databases are inaccessible."


def get_tools() -> list:
    return [
        {
            "name": "browser_history",
            "description": "Return recent browser history (URLs and titles) from Chrome, Edge, or Brave.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of history entries to return (default 25)."
                    },
                    "browser": {
                        "type": "string",
                        "description": "Filter to a specific browser: chrome, edge, brave. Empty for first found."
                    }
                },
                "required": []
            },
            "handler": _browser_history
        }
    ]
