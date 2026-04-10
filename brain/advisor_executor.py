"""Tier 3 Cloud Advisor: Anthropic SDK integration with cost tracking."""

import json
import logging
import os
from collections.abc import AsyncIterator
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(r"C:\jarvis\.env")

logger = logging.getLogger("jarvis.advisor")

# Dedicated advisor log
ADVISOR_LOG = Path(r"C:\jarvis\logs\advisor.log")
ADVISOR_LOG.parent.mkdir(parents=True, exist_ok=True)
_fh = logging.FileHandler(ADVISOR_LOG, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
logger.addHandler(_fh)
logger.setLevel(logging.INFO)

# Cost tracking
COSTS_LOG = Path(r"C:\jarvis\logs\costs.log")
DAILY_LIMIT_USD = float(os.getenv("TIER3_CLOUD_DAILY_LIMIT_USD", "2.00"))
CLOUD_MODEL = os.getenv("TIER3_CLOUD_MODEL", "claude-sonnet-4-5-20250929")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TIER3_MODE = os.getenv("TIER3_MODE", "ask_user")

# Sonnet 4 pricing (per million tokens)
_PRICING = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
}
_DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def _get_today_spend() -> float:
    """Sum today's cloud spend from costs.log."""
    today = date.today().isoformat()
    total = 0.0
    if not COSTS_LOG.exists():
        return 0.0
    for line in COSTS_LOG.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
            if entry.get("date") == today:
                total += entry.get("cost_usd", 0.0)
        except (json.JSONDecodeError, KeyError):
            pass
    return total


def _log_cost(tokens_in: int, tokens_out: int, model: str) -> float:
    """Log token usage and cost. Returns cost in USD."""
    pricing = _PRICING.get(model, _DEFAULT_PRICING)
    cost = (tokens_in * pricing["input"] + tokens_out * pricing["output"]) / 1_000_000
    entry = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost, 6),
    }
    COSTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(COSTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info("Cost logged: $%.6f (%d in / %d out) model=%s", cost, tokens_in, tokens_out, model)
    return cost


async def run_cloud_advisor(user_message: str, system_prompt: str,
                            memories: list[str] | None = None) -> AsyncIterator[dict[str, Any]]:
    """Call Anthropic cloud advisor and stream results."""
    if not ANTHROPIC_API_KEY:
        yield {"type": "text", "content": "Sir, cloud advisor is not configured. Set ANTHROPIC_API_KEY in .env."}
        return

    # Budget check
    today_spend = _get_today_spend()
    if today_spend >= DAILY_LIMIT_USD:
        yield {"type": "text",
               "content": f"Sir, today's advisor budget is exhausted (${today_spend:.2f} / ${DAILY_LIMIT_USD:.2f}). "
                          f"Falling back to local Tier 3."}
        # Fallback to local tier 3
        from brain.models import get_model_for_tier
        import ollama
        local_cfg = get_model_for_tier(3, preference="local")
        yield {"type": "routing", "tier": 3, "reason": "Budget exceeded, using local advisor."}
        full_text = ""
        msgs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        for chunk in ollama.chat(model=local_cfg.model_name, messages=msgs, stream=True):
            token = chunk.get("message", {}).get("content", "")
            if token:
                full_text += token
                yield {"type": "token", "content": token}
        if full_text:
            from brain.memory import append as log_backup
            from brain.memory_mem0 import add_memory
            add_memory(user_message, "user")
            add_memory(full_text, "assistant")
            log_backup("user", user_message)
            log_backup("assistant", full_text)
        return

    yield {"type": "text", "content": f"Engaging cloud advisor (${today_spend:.2f} / ${DAILY_LIMIT_USD:.2f} today)..."}

    # Build Anthropic messages
    advisor_system = system_prompt + """

# Advisor Mode
You are operating as the Tier 3 Cloud Advisor. Provide structured, strategic analysis.
When the task involves implementation, return a PLAN with numbered steps that can be executed locally.
Format plans as:
## Plan
1. Step description | file: path | action: create/edit/delete
2. ...

## Reasoning
Why this approach is optimal.

## Risks
What could go wrong and mitigations.
"""
    if memories:
        advisor_system += "\n# Relevant Memories\n" + "\n".join(f"- {m}" for m in memories)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        full_text = ""
        with client.messages.stream(
            model=CLOUD_MODEL,
            max_tokens=4096,
            system=advisor_system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                yield {"type": "token", "content": text}

        # Log cost
        usage = stream.get_final_message().usage
        tokens_in = usage.input_tokens
        tokens_out = usage.output_tokens
        cost = _log_cost(tokens_in, tokens_out, CLOUD_MODEL)

        logger.info("Advisor response: %d chars, $%.6f", len(full_text), cost)

        # Save to memory
        from brain.memory import append as log_backup
        from brain.memory_mem0 import add_memory
        add_memory(user_message, "user")
        add_memory(full_text, "assistant")
        log_backup("user", user_message)
        log_backup("assistant", full_text)

    except Exception as e:
        logger.error("Cloud advisor failed: %s", e)
        yield {"type": "text", "content": f"Cloud advisor encountered an error, Sir: {e}. Falling back to local."}
        # Fallback to local
        import ollama
        from brain.models import get_model_for_tier
        local_cfg = get_model_for_tier(3, preference="local")
        full_text = ""
        msgs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        for chunk in ollama.chat(model=local_cfg.model_name, messages=msgs, stream=True):
            token = chunk.get("message", {}).get("content", "")
            if token:
                full_text += token
                yield {"type": "token", "content": token}
