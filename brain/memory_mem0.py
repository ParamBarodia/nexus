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

# Note: user_id is the primary key for the person JARVIS serves (Param)
USER_ID = "param"

# Lazy init with retry: Mem0 needs Ollama + nomic-embed-text. If those aren't
# ready when this module is imported (e.g. brain boots before Ollama), we DON'T
# permanently give up — we retry on first use so memory self-heals once Ollama is up.
_m = None
_last_attempt = 0.0
_RETRY_COOLDOWN = 30.0  # seconds between re-init attempts while still failing


def _get_memory():
    """Return the Mem0 instance, initializing lazily (with throttled retry)."""
    global _m, _last_attempt
    if _m is not None:
        return _m
    import time
    now = time.monotonic()
    if now - _last_attempt < _RETRY_COOLDOWN:
        return None
    _last_attempt = now
    try:
        _m = Memory.from_config(config)
        mem_logger.info("Mem0 initialized (lazy).")
    except Exception as e:
        mem_logger.warning("Mem0 not ready yet (Ollama/nomic-embed-text?): %s", e)
        _m = None
    return _m


def add_memory(message: str, role: str):
    """Store raw fact from conversation."""
    mem = _get_memory()
    if mem is None:
        return
    try:
        # infer=False stores the raw turn via embeddings WITHOUT an LLM fact-extraction
        # pass. Extraction hammers the local model and serializes behind chat requests,
        # making every turn slow. Raw storage still gives semantic recall on search.
        mem.add(message, user_id=USER_ID, metadata={"role": role}, infer=False)
        mem_logger.info("Memory added from %s: %s", role, message[:100])
    except Exception as e:
        mem_logger.error("Failed to add memory: %s", e)


def get_memories(query: str, limit: int = 5):
    """Retrieve top N relevant memories."""
    mem = _get_memory()
    if mem is None:
        return []
    try:
        # Mem0 2.x API: scope by filters={"user_id": ...}; results come back as {"results": [...]}.
        results = mem.search(query, filters={"user_id": USER_ID}, limit=limit)
        items = results.get("results", []) if isinstance(results, dict) else results
        memories = []
        for r in items:
            if isinstance(r, dict) and "memory" in r:
                memories.append(r["memory"])
            elif isinstance(r, str):
                memories.append(r)
        return memories
    except Exception as e:
        mem_logger.error("Failed to search memory: %s", e)
        return []


def get_all_memories():
    """Return all stored facts for stats/CLI (list of memory dicts)."""
    mem = _get_memory()
    if mem is None:
        return []
    try:
        res = mem.get_all(filters={"user_id": USER_ID})
        return res.get("results", []) if isinstance(res, dict) else res
    except Exception as e:
        mem_logger.error("Failed to get all memories: %s", e)
        return []
