"""Domain mode management."""

import logging
from typing import Dict, Any

logger = logging.getLogger("jarvis.modes")

MODES = {
    "personal": {
        "description": "General life, health, and personal goals.",
        "prompt_extension": "Focus on balance, health, and intellectual freedom. Be more conversational but remain formal.",
        "priority_projects": []
    },
    "office": {
        "description": "Primary work / job.",
        "prompt_extension": "Focus on work efficiency, deliverables, and deep-work priorities. Be strictly analytical.",
        "priority_projects": []
    },
    "content": {
        "description": "Content creation and social media.",
        "prompt_extension": "Focus on clarity, hooks, and technical storytelling. Be slightly more creative while maintaining the JARVIS persona.",
        "priority_projects": []
    },
    "freelance": {
        "description": "Client work and external projects.",
        "prompt_extension": "Focus on deadlines, client requirements, and high-quality deliverables.",
        "priority_projects": []
    }
}

_current_mode = "personal"

def set_mode(mode_name: str) -> bool:
    global _current_mode
    if mode_name in MODES:
        _current_mode = mode_name
        logger.info("Mode switched to: %s", mode_name)
        return True
    return False

def get_current_mode() -> str:
    return _current_mode

def get_mode_info(mode_name: str) -> Dict[str, Any]:
    return MODES.get(mode_name, MODES["personal"])
