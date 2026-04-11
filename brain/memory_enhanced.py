"""Enhanced memory layer wrapping Mem0 — episodic summaries, preference extraction,
temporal decay, and contradiction detection."""

import json
import logging
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from brain.memory_mem0 import add_memory as _raw_add, get_memories as _raw_get, get_all_memories as _raw_get_all

logger = logging.getLogger("jarvis.memory_enhanced")

EPISODES_DIR = Path(r"C:\jarvis\data\episodes")
EPISODES_DIR.mkdir(parents=True, exist_ok=True)

# Temporal decay: 30-day half-life
HALF_LIFE_DAYS = 30


def _decay_weight(memory_date_str: str) -> float:
    """Compute a temporal decay weight for a memory based on its age."""
    try:
        mem_date = datetime.fromisoformat(memory_date_str).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.5  # unknown date, give neutral weight
    age_days = (datetime.now(timezone.utc) - mem_date).days
    return math.exp(-0.693 * age_days / HALF_LIFE_DAYS)  # 0.693 = ln(2)


def get_memories_weighted(query: str, top_k: int = 10) -> list[str]:
    """Retrieve memories with temporal decay weighting.

    Falls back to standard retrieval if weighting is not possible.
    """
    raw = _raw_get(query)
    if not raw:
        return []

    # If memories are plain strings (no metadata), return as-is
    if isinstance(raw[0], str):
        return raw[:top_k]

    # If memories have metadata with timestamps, apply decay
    try:
        weighted = []
        for mem in raw:
            if isinstance(mem, dict):
                text = mem.get("text", str(mem))
                ts = mem.get("created_at", mem.get("timestamp", ""))
                weight = _decay_weight(ts) if ts else 0.5
                weighted.append((weight, text))
            else:
                weighted.append((0.5, str(mem)))

        weighted.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in weighted[:top_k]]
    except Exception as e:
        logger.warning("Weighted retrieval failed, using raw: %s", e)
        return [str(m) for m in raw[:top_k]]


def extract_preferences(user_msg: str, assistant_msg: str) -> list[str]:
    """Extract 'prefers X over Y' patterns from a conversation turn."""
    preferences = []
    lower_u = user_msg.lower()
    lower_a = assistant_msg.lower()

    # Simple heuristic patterns
    preference_signals = [
        "i prefer", "i like", "i want", "don't like", "i hate",
        "always use", "never use", "switch to", "instead of",
    ]
    for signal in preference_signals:
        if signal in lower_u:
            # Extract a preference snippet (up to 100 chars around the signal)
            idx = lower_u.index(signal)
            start = max(0, idx - 20)
            end = min(len(user_msg), idx + 80)
            snippet = user_msg[start:end].strip()
            preferences.append(f"User preference: {snippet}")

    return preferences


def save_episode_entry(user_msg: str, assistant_msg: str):
    """Append a conversation turn to today's episode file."""
    today = date.today().isoformat()
    episode_file = EPISODES_DIR / f"{today}.json"

    entries = []
    if episode_file.exists():
        try:
            entries = json.loads(episode_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            entries = []

    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": user_msg[:500],
        "assistant": assistant_msg[:500],
    })

    episode_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def check_contradiction(new_memory: str) -> str | None:
    """Search existing memories for potential contradictions with new_memory.

    Returns a warning string if a contradiction is detected, else None.
    """
    existing = _raw_get(new_memory)
    if not existing:
        return None

    # Simple heuristic: look for negation patterns
    negations = [
        ("prefer", "don't prefer"), ("like", "don't like"),
        ("always", "never"), ("enable", "disable"),
        ("use", "don't use"), ("want", "don't want"),
    ]

    new_lower = new_memory.lower()
    for mem in existing[:5]:
        mem_lower = str(mem).lower() if not isinstance(mem, str) else mem.lower()
        for pos, neg in negations:
            if (pos in new_lower and neg in mem_lower) or (neg in new_lower and pos in mem_lower):
                return f"Potential contradiction with existing memory: '{str(mem)[:100]}'"
    return None


def add_memory_enhanced(content: str, role: str, user_msg: str = "", assistant_msg: str = ""):
    """Enhanced memory addition with preference extraction and contradiction detection."""
    # Check for contradictions
    contradiction = check_contradiction(content)
    if contradiction:
        logger.warning("Memory contradiction detected: %s", contradiction)

    # Add to Mem0
    _raw_add(content, role)

    # Extract and store preferences
    if role == "assistant" and user_msg:
        prefs = extract_preferences(user_msg, content)
        for pref in prefs:
            _raw_add(pref, "system")
            logger.info("Preference extracted: %s", pref[:80])

    # Save episode entry
    if user_msg and assistant_msg:
        save_episode_entry(user_msg, assistant_msg)


def get_episode_summary(target_date: str | None = None) -> str:
    """Get a summary of conversations for a given date."""
    target = target_date or date.today().isoformat()
    episode_file = EPISODES_DIR / f"{target}.json"

    if not episode_file.exists():
        return f"No conversation episodes for {target}."

    try:
        entries = json.loads(episode_file.read_text(encoding="utf-8"))
        summary_parts = [f"Episode log for {target} ({len(entries)} turns):"]
        for entry in entries[:20]:
            summary_parts.append(f"  User: {entry['user'][:80]}...")
        return "\n".join(summary_parts)
    except Exception as e:
        return f"Failed to read episodes: {e}"
