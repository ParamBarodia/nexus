"""Search for files on the local filesystem."""

import json
import subprocess


def _file_search(query: str = "", path: str = "C:\\", max_results: int = 20) -> str:
    """Search for files matching a name pattern.

    Args:
        query: Filename or glob pattern to search for (e.g. '*.pdf', 'report').
        path: Root directory to search in (default C:\\).
        max_results: Maximum number of results to return (default 20).
    """
    if not query:
        return "Error: 'query' parameter is required."

    max_results = int(max_results) if max_results else 20

    # Try 'where' command first (searches PATH-like locations)
    # Then fall back to 'dir /s /b'
    methods = [
        _search_with_dir,
        _search_with_where,
    ]

    for method in methods:
        try:
            results = method(query, path, max_results)
            if results is not None:
                return json.dumps({"query": query, "path": path, "count": len(results), "files": results}, indent=2)
        except Exception:
            continue

    return json.dumps({"query": query, "path": path, "count": 0, "files": [], "note": "No results found or search failed."})


def _search_with_dir(query: str, path: str, max_results: int) -> list | None:
    """Use 'dir /s /b' to search recursively."""
    cmd = f'dir /s /b "{path}\\*{query}*"'
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 and not result.stdout.strip():
        return None
    lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
    return lines[:max_results] if lines else None


def _search_with_where(query: str, path: str, max_results: int) -> list | None:
    """Use 'where /r' to search recursively."""
    cmd = f'where /r "{path}" "*{query}*"'
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 and not result.stdout.strip():
        return None
    lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
    return lines[:max_results] if lines else None


def get_tools() -> list:
    return [
        {
            "name": "file_search",
            "description": "Search for files by name pattern on the local filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Filename or pattern to search for (e.g. '*.pdf', 'report')."
                    },
                    "path": {
                        "type": "string",
                        "description": "Root directory to search in (default 'C:\\\\')."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default 20)."
                    }
                },
                "required": ["query"]
            },
            "handler": _file_search
        }
    ]
