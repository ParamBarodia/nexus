"""Conversation memory management for Jarvis brain."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("jarvis.memory")

MEMORY_FILE = Path(r"C:\jarvis\data\memory.json")
MAX_ENTRIES = 100


def load_memory() -> list[dict[str, Any]]:
    """Load full conversation history from disk."""
    try:
        if MEMORY_FILE.exists():
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        return []
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load memory: %s", e)
        return []


def _save(entries: list[dict[str, Any]]) -> None:
    """Write memory entries to disk."""
    try:
        MEMORY_FILE.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        logger.error("Failed to save memory: %s", e)


def append(role: str, content: str) -> None:
    """Append a message to memory and save immediately."""
    entries = load_memory()
    entries.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Keep only the last MAX_ENTRIES
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    _save(entries)
    logger.info("Memory appended: role=%s, length=%d", role, len(content))


def get_recent(n: int = 20) -> list[dict[str, str]]:
    """Return the last n entries as role/content dicts for LLM context."""
    entries = load_memory()
    recent = entries[-n:] if len(entries) > n else entries
    return [{"role": e["role"], "content": e["content"]} for e in recent]


def clear() -> None:
    """Clear all conversation memory."""
    _save([])
    logger.info("Memory cleared")
