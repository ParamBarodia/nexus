"""Skills loader: markdown-based behavior extensions for JARVIS."""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("jarvis.skills")

SKILLS_DIR = Path(r"C:\jarvis\brain\skills")

_skills_registry: list[dict[str, Any]] = []


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML-like frontmatter from markdown."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_block = content[3:end].strip()
    body = content[end + 3:].strip()
    meta = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()
    return meta, body


def load_skills() -> list[dict[str, Any]]:
    """Load all skill definitions from brain/skills/."""
    global _skills_registry
    _skills_registry = []

    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    for md_file in SKILLS_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(content)
            skill = {
                "name": meta.get("name", md_file.stem),
                "description": meta.get("description", ""),
                "triggers": [t.strip() for t in meta.get("triggers", "").split(",") if t.strip()],
                "tools": [t.strip() for t in meta.get("tools", "").split(",") if t.strip()],
                "tier": int(meta.get("tier", "1")),
                "prompt_extension": body,
                "file": md_file.name,
            }
            _skills_registry.append(skill)
            logger.info("Loaded skill: %s (%d triggers)", skill["name"], len(skill["triggers"]))
        except Exception as e:
            logger.error("Failed to load skill %s: %s", md_file.name, e)

    logger.info("Total skills loaded: %d", len(_skills_registry))
    return _skills_registry


def get_skills() -> list[dict[str, Any]]:
    """Return current skills registry."""
    if not _skills_registry:
        load_skills()
    return _skills_registry


def match_skill(message: str) -> dict[str, Any] | None:
    """Check if a message triggers any skill. Returns first match or None."""
    if not _skills_registry:
        load_skills()
    lower = message.lower()
    for skill in _skills_registry:
        for trigger in skill["triggers"]:
            if trigger.lower() in lower:
                logger.info("Skill matched: %s (trigger: %s)", skill["name"], trigger)
                return skill
    return None
