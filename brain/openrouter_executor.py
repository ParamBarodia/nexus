"""Free 'smart tier' via OpenRouter (OpenAI-compatible).

Routes hard/conversational Tier-3 queries to a FREE frontier model. Cost is always
$0 (free models only). Free models are aggressively rate-limited, so this:
  - fails fast (no SDK retries, short timeout),
  - tries SEVERAL free models in order (if one is 429, try the next),
  - does web search by injection (reliable) instead of slow tool-probing,
  - falls back to the local Tier-3 model if every free model is unavailable.
So it never costs a penny and never hangs/breaks.
"""

import asyncio
import time
import logging
from collections.abc import AsyncIterator
from typing import Any

from brain.models import OPENROUTER_API_KEY, OPENROUTER_MODEL, TIER3_LOCAL_MODEL
from brain.mcp_client import mcp

logger = logging.getLogger("jarvis.openrouter")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# Try the configured model first, then one strong free fallback, then give up to local.
# Kept short so worst-case latency (all rate-limited) stays bounded before local fallback.
_FALLBACK_FREE = [
    "openai/gpt-oss-120b:free",
]

WEB_HINTS = ("latest", "current", "today", "news", "search", "right now", "this week",
             "2026", "price of", "weather", "who won", "recent")

# Rate-limit cooldown: once a free model returns 429, skip it for a while so we don't
# waste time hitting a known-limited model on every request.
_COOLDOWN: dict[str, float] = {}
_COOLDOWN_SECONDS = 300  # 5 minutes


def _client():
    from openai import OpenAI
    # max_retries=0 + short timeout so a slow/limited free model fails FAST and we fall
    # back to local quickly. Worst case ~2 models x 15s + local ≈ well under a minute.
    return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE, max_retries=0, timeout=15)


def _available_models() -> list[str]:
    """Free models not currently in rate-limit cooldown, in priority order."""
    now = time.monotonic()
    out: list[str] = []
    for m in [OPENROUTER_MODEL] + _FALLBACK_FREE:
        if m and m not in out and _COOLDOWN.get(m, 0.0) < now:
            out.append(m)
    return out


def _is_rate_limit(err: Exception) -> bool:
    s = str(err).lower()
    return "429" in s or "rate" in s or err.__class__.__name__ == "RateLimitError"


async def run_openrouter_advisor(user_message: str, system_prompt: str,
                                 memories: list | None = None,
                                 tools: list | None = None) -> AsyncIterator[dict[str, Any]]:
    """Stream from a free OpenRouter model; try several, then fall back to local."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    from brain.chat import _aiter_blocking  # thread->queue bridge (keeps the loop free)

    # Web search by injection (reliable across all models) when the query needs current info.
    if any(h in user_message.lower() for h in WEB_HINTS):
        try:
            # Blocking network call — off-thread it so the event loop stays responsive.
            results = await asyncio.to_thread(mcp.call_tool, "web_search", {"query": user_message})
            yield {"type": "tool_call", "tool": "web_search", "args": {"query": user_message}}
            yield {"type": "tool_result", "tool": "web_search", "result": str(results)[:200]}
            messages.insert(1, {"role": "system",
                                "content": f"Current web search results to use:\n{str(results)[:2500]}"})
        except Exception as e:
            logger.warning("web_search inject failed: %s", e)

    client = _client()
    candidates = _available_models()
    for model in candidates:
        try:
            full_text = ""
            # The OpenAI SDK's streaming response is a BLOCKING generator; drive it from a
            # worker thread via the bridge so tokens don't freeze uvicorn's event loop.
            async for chunk in _aiter_blocking(
                lambda m=model: client.chat.completions.create(model=m, messages=messages, stream=True)
            ):
                tok = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                if tok:
                    full_text += tok
                    yield {"type": "token", "content": tok}
            if full_text:
                yield {"type": "_save", "user": user_message, "assistant": full_text}
            return  # success
        except Exception as e:
            if _is_rate_limit(e):
                _COOLDOWN[model] = time.monotonic() + _COOLDOWN_SECONDS  # skip it for 5 min
                logger.warning("Free model %s rate-limited — cooling down 5m, trying next.", model)
            else:
                logger.warning("Free model %s error (%s) — trying next.", model, type(e).__name__)
            continue

    # Every free model is rate-limited/offline → local fallback (free, always available).
    if not candidates:
        logger.info("All free models in cooldown; using local %s directly.", TIER3_LOCAL_MODEL)
    else:
        logger.info("All free models unavailable; falling back to local %s", TIER3_LOCAL_MODEL)
    from brain.chat import _run_ollama_chat
    async for chunk in _run_ollama_chat(TIER3_LOCAL_MODEL, messages, None, user_message):
        yield chunk
