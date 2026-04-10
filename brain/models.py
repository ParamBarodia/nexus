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

TIER1_MODEL = "gemma2:2b"
TIER2_MODEL = os.getenv("TIER2_MODEL", "qwen2.5:7b")
TIER3_LOCAL_MODEL = os.getenv("TIER3_LOCAL_MODEL", "qwen2.5:14b")
TIER3_CLOUD_ENABLED = os.getenv("TIER3_CLOUD_ENABLED", "false").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TIER3_MODE = os.getenv("TIER3_MODE", "ask_user")

def get_model_for_tier(tier: int, preference: Optional[str] = None) -> ModelConfig:
    """Return model config for a given tier."""
    if tier == 1:
        return ModelConfig(tier=1, model_name=TIER1_MODEL, provider="ollama")
    elif tier == 2:
        return ModelConfig(tier=2, model_name=TIER2_MODEL, provider="ollama")
    elif tier == 3:
        if preference == "cloud" and TIER3_CLOUD_ENABLED and ANTHROPIC_API_KEY:
            return ModelConfig(tier=3, model_name="claude-3-5-sonnet-20241022", provider="anthropic")
        # Default to local TIER3
        return ModelConfig(tier=3, model_name=TIER3_LOCAL_MODEL, provider="ollama")
    
    # Default to tier 1
    return ModelConfig(tier=1, model_name=TIER1_MODEL, provider="ollama")
