"""List top processes by memory or CPU usage."""

import json


def _process_monitor(sort_by: str = "memory", limit: int = 15) -> str:
    """List top processes sorted by memory or CPU usage.

    Args:
        sort_by: 'memory' or 'cpu' (default 'memory').
        limit: Number of processes to return (default 15).
    """
    try:
        import psutil
    except ImportError:
        return "Error: psutil is not installed. Run: pip install psutil"

    limit = int(limit) if limit else 15
    sort_by = (sort_by or "memory").lower().strip()

    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
            try:
                info = p.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "memory_mb": round((info["memory_info"].rss / 1024 / 1024), 1) if info["memory_info"] else 0,
                    "cpu_percent": info["cpu_percent"] or 0.0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if sort_by == "cpu":
            procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        else:
            procs.sort(key=lambda x: x["memory_mb"], reverse=True)

        top = procs[:limit]
        total_mem = psutil.virtual_memory()
        summary = {
            "sort_by": sort_by,
            "total_memory_gb": round(total_mem.total / 1024 / 1024 / 1024, 1),
            "used_memory_percent": total_mem.percent,
            "processes": top
        }
        return json.dumps(summary, indent=2)
    except Exception as e:
        return f"Process monitor failed: {e}"


def get_tools() -> list:
    return [
        {
            "name": "process_monitor",
            "description": "List the top processes by memory or CPU usage, with system memory summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sort_by": {
                        "type": "string",
                        "description": "Sort criterion: 'memory' or 'cpu' (default 'memory')."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of processes to return (default 15)."
                    }
                },
                "required": []
            },
            "handler": _process_monitor
        }
    ]
