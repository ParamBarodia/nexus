"""Nexus chat engine: routing, memory, and multi-tier execution."""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, List

import ollama
from brain.memory import append as log_backup
from brain.memory_mem0 import add_memory, get_memories
from brain.prompt import build_system_prompt
from brain.router import classify_message
from brain.models import get_model_for_tier
from brain.mcp_client import mcp

logger = logging.getLogger("jarvis.chat")

async def stream_chat(user_message: str, force_tier: int = None) -> AsyncIterator[dict[str, Any]]:
    """Nexus chat flow: Router -> Tier -> Tools -> Mem0."""
    
    # 1. Routing
    if force_tier:
        decision = {"tier": force_tier, "confidence": 1.0, "reason": "Explicitly requested by user."}
    else:
        decision = classify_message(user_message)
    
    tier = decision["tier"]
    model_cfg = get_model_for_tier(tier)
    
    yield {"type": "routing", "tier": tier, "reason": decision["reason"]}
    logger.info("Routing: Tier %d (%s)", tier, model_cfg.model_name)

    # 2. Context Building (Mem0 Inject)
    memories = get_memories(user_message)
    system_prompt = build_system_prompt()
    if memories:
        system_prompt += "\n# Relevant Background (Memory)\n" + "\n".join(f"- {m}" for m in memories)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    # 3. Execution (Ollama / Anthropic)
    try:
        if model_cfg.provider == "ollama":
            # Multi-tier handles tool calls differently
            # Tier 1 & 2 use Ollama tools
            tools = mcp.get_tool_definitions() if tier >= 2 or "time" in user_message or "search" in user_message else None
            
            response = ollama.chat(
                model=model_cfg.model_name,
                messages=messages,
                tools=tools,
                stream=False
            )
            
            message = response.get("message", {})
            tool_calls = message.get("tool_calls", None)

            if tool_calls:
                messages.append(message)
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name")
                    args = func.get("arguments", {})
                    
                    yield {"type": "tool_call", "tool": name, "args": args}
                    result = mcp.call_tool(name, args)
                    yield {"type": "tool_result", "tool": name, "result": result}
                    
                    messages.append({"role": "tool", "content": result})

                # Final follow-up
                full_text = ""
                for chunk in ollama.chat(model=model_cfg.model_name, messages=messages, stream=True):
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_text += token
                        yield {"type": "token", "content": token}
                
                # Mem0 Extract & Backups
                if full_text:
                    add_memory(user_message, "user")
                    add_memory(full_text, "assistant")
                    log_backup("user", user_message)
                    log_backup("assistant", full_text)

            else:
                # No tools, stream directly
                full_text = ""
                for chunk in ollama.chat(model=model_cfg.model_name, messages=messages, stream=True):
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_text += token
                        yield {"type": "token", "content": token}
                
                if full_text:
                    # Async memory update
                    add_memory(user_message, "user")
                    add_memory(full_text, "assistant")
                    log_backup("user", user_message)
                    log_backup("assistant", full_text)

        elif model_cfg.provider == "anthropic":
            # Cloud Tier 3 logic (placeholder for actual SDK usage)
            yield {"type": "text", "content": "Sir, I am escalating to Cloud Advisor (Sonnet)..."}
            # Mock implementation for now
            yield {"type": "token", "content": "As a Tier 3 Advisor, I have analyzed your request... (Cloud Simulation)"}
            yield {"type": "done"}
            return

    except Exception as e:
        logger.error("Chat failure: %s", e)
        yield {"type": "text", "content": f"I'm afraid I've encountered a system failure, Sir: {e}"}

    yield {"type": "done"}
