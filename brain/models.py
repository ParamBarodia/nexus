"""Model registry and selection for Nexus multi-tier brain."""

import os
import logging
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env
load_dotenv(dotenv_path=r"C:\jarvis\.env")

logger = logging.getLogger("jarvis.models")

class ModelConfig(BaseModel):
    tier: int
    model_name: str
    provider: str  # "ollama" or "anthropic"

TIER1_MODEL = os.getenv("TIER1_MODEL", "llama3.2:3b")
TIER2_MODEL = os.getenv("TIER2_MODEL", "gemma3:4b")
TIER3_LOCAL_MODEL = os.getenv("TIER3_LOCAL_MODEL", "hermes3:8b")
TIER3_CLOUD_ENABLED = os.getenv("TIER3_CLOUD_ENABLED", "false").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TIER3_MODE = os.getenv("TIER3_MODE", "ask_user")

# Free "smart tier" via OpenRouter (free models only; $0). Used for hard/conversational
# Tier-3 queries when enabled; falls back to the local Tier-3 model if unavailable.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TIER3_OPENROUTER_ENABLED = os.getenv("TIER3_OPENROUTER_ENABLED", "false").lower() == "true"
OPENROUTER_MODEL = os.getenv("TIER3_OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

def get_model_for_tier(tier: int, preference: Optional[str] = None) -> ModelConfig:
    """Return model config for a given tier."""
    if tier == 1:
        return ModelConfig(tier=1, model_name=TIER1_MODEL, provider="ollama")
    elif tier == 2:
        return ModelConfig(tier=2, model_name=TIER2_MODEL, provider="ollama")
    elif tier == 3:
        if preference == "local":
            return ModelConfig(tier=3, model_name=TIER3_LOCAL_MODEL, provider="ollama")
        # Prefer the FREE OpenRouter smart model when enabled (no cost).
        if TIER3_OPENROUTER_ENABLED and OPENROUTER_API_KEY:
            return ModelConfig(tier=3, model_name=OPENROUTER_MODEL, provider="openrouter")
        # Optional paid Anthropic path (off by default).
        if TIER3_CLOUD_ENABLED and ANTHROPIC_API_KEY:
            return ModelConfig(tier=3, model_name=os.getenv("TIER3_CLOUD_MODEL", "claude-sonnet-4-6"), provider="anthropic")
        return ModelConfig(tier=3, model_name=TIER3_LOCAL_MODEL, provider="ollama")
    
    # Default to tier 1
    return ModelConfig(tier=1, model_name=TIER1_MODEL, provider="ollama")
