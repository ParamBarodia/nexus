"""Mem0 integration for high-fidelity memory management."""

import os
import logging
from mem0 import Memory
from brain.models import TIER1_MODEL

# Setup dedicated memory log
LOG_FILE = r"C:\jarvis\logs\memory.log"
mem_logger = logging.getLogger("jarvis.memory_mem0")
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
mem_logger.addHandler(fh)
mem_logger.setLevel(logging.INFO)

config = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "path": r"C:\jarvis\data\chroma",
        }
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": TIER1_MODEL,
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
        }
    }
}

# Initialize Mem0
# Note: user_id is the primary key for the person JARVIS serves (Param)
USER_ID = "param"
m = Memory.from_config(config)

def add_memory(message: str, role: str):
    """Store raw fact from conversation."""
    try:
        m.add(message, user_id=USER_ID, metadata={"role": role})
        mem_logger.info("Memory added from %s: %s", role, message[:100])
    except Exception as e:
        mem_logger.error("Failed to add memory: %s", e)

def get_memories(query: str):
    """Retrieve top N relevant memories."""
    try:
        results = m.search(query, user_id=USER_ID, limit=5)
        # Ensure results is a list of dicts
        memories = []
        for r in results:
            if isinstance(r, dict) and "memory" in r:
                memories.append(r["memory"])
            elif isinstance(r, str):
                memories.append(r)
        return memories
    except Exception as e:
        mem_logger.error("Failed to search memory: %s", e)
        return []

def get_all_memories():
    """Return all stored facts for stats/CLI."""
    try:
        return m.get_all(user_id=USER_ID)
    except Exception as e:
        mem_logger.error("Failed to get all memories: %s", e)
        return []
