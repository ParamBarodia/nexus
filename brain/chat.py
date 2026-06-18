"""Nexus chat engine: routing, memory, and multi-tier execution."""

import asyncio
import json
import logging
import threading
from collections.abc import AsyncIterator
from typing import Any, Callable, Iterable

import ollama
from brain.memory import append as log_backup
from brain.memory_enhanced import add_memory_enhanced, get_memories_weighted
from brain.prompt import build_system_prompt
from brain.router import classify_message
from brain.models import get_model_for_tier
from brain.mcp_client import mcp
from brain.skills_loader import match_skill

logger = logging.getLogger("jarvis.chat")


def _persist_memory_async(user_msg: str, assistant_msg: str) -> None:
    """Save the turn to memory in a BACKGROUND thread.

    Mem0's add() runs an LLM fact-extraction pass (~10-20s locally); doing it inline
    blocks the response. Backgrounding it makes replies return immediately.
    """
    import threading

    def _work():
        try:
            # Lightweight raw storage (no LLM extraction) so it doesn't hog the local model.
            from brain.memory_mem0 import add_memory as _raw_add
            _raw_add(user_msg, "user")
            _raw_add(assistant_msg, "assistant")
            log_backup("user", user_msg)
            log_backup("assistant", assistant_msg)
        except Exception as e:
            logger.error("Async memory persist failed: %s", e)

    threading.Thread(target=_work, daemon=True).start()


def _needs_tools(message: str) -> bool:
    """Check if a message likely needs tool access (auto-derived from registered MCP tools)."""
    lower = message.lower()
    return any(name.replace("_", " ") in lower for name in mcp.tools.keys())


_BRIDGE_DONE = object()


async def _aiter_blocking(make_gen: Callable[[], Iterable[Any]]) -> AsyncIterator[Any]:
    """Drive a BLOCKING (synchronous) generator from a worker thread and yield its
    items to the async caller WITHOUT blocking the event loop.

    Ollama's streaming response is a synchronous generator; iterating it inline inside
    an async function freezes uvicorn's single event loop on every token. We run the
    iteration in a thread and hand tokens back through an asyncio.Queue.
    """
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue(maxsize=256)

    def _producer():
        try:
            for item in make_gen():
                loop.call_soon_threadsafe(q.put_nowait, ("item", item))
        except Exception as e:  # surface the error to the consumer
            loop.call_soon_threadsafe(q.put_nowait, ("error", e))
        finally:
            loop.call_soon_threadsafe(q.put_nowait, ("done", _BRIDGE_DONE))

    threading.Thread(target=_producer, daemon=True).start()

    while True:
        kind, payload = await q.get()
        if kind == "done":
            break
        if kind == "error":
            raise payload
        yield payload


async def _stream_reply(model_name: str, messages: list,
                        user_message: str) -> AsyncIterator[dict[str, Any]]:
    """Stream a plain (no-tool) reply through the thread->queue bridge."""
    full_text = ""
    async for chunk in _aiter_blocking(
        lambda: ollama.chat(model=model_name, messages=messages, stream=True)
    ):
        token = chunk.get("message", {}).get("content", "")
        if token:
            full_text += token
            yield {"type": "token", "content": token}
    if full_text:
        yield {"type": "_save", "user": user_message, "assistant": full_text}


async def _run_ollama_chat(model_name: str, messages: list, tools: list | None,
                           user_message: str) -> AsyncIterator[dict[str, Any]]:
    """Execute an Ollama chat with optional tools and streaming follow-up.

    All blocking Ollama / tool calls run in worker threads so the event loop stays
    responsive (the dashboard and other requests don't freeze during generation).
    """
    # Fast path: no tools requested -> stream directly. (Previously this still ran a
    # wasteful non-streaming generation first, doubling latency for every reply.)
    if not tools:
        async for chunk in _stream_reply(model_name, messages, user_message):
            yield chunk
        return

    # Tools path: one non-streaming probe to see whether the model wants a tool.
    try:
        response = await asyncio.to_thread(
            lambda: ollama.chat(model=model_name, messages=messages, tools=tools, stream=False)
        )
    except Exception as e:
        # Some models (e.g. gemma3) don't support tool calling — degrade gracefully
        # by streaming a normal reply instead.
        if "does not support tools" in str(e).lower():
            logger.warning("%s lacks tool support; streaming without tools.", model_name)
            async for chunk in _stream_reply(model_name, messages, user_message):
                yield chunk
            return
        raise

    message = response.get("message", {})
    tool_calls = message.get("tool_calls", None)

    if not tool_calls:
        # No tool needed — the probe already produced the full reply; emit it directly
        # instead of regenerating the whole thing a second time.
        text = message.get("content", "")
        if text:
            yield {"type": "token", "content": text}
            yield {"type": "_save", "user": user_message, "assistant": text}
        return

    # The model wants tools — run them, then stream the follow-up answer.
    messages.append(message)
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name")
        args = func.get("arguments", {})

        yield {"type": "tool_call", "tool": name, "args": args}
        # Tool handlers may themselves block (subprocess, network) — off-thread it.
        result = await asyncio.to_thread(mcp.call_tool, name, args)
        yield {"type": "tool_result", "tool": name, "result": result}
        messages.append({"role": "tool", "content": result})

    async for chunk in _stream_reply(model_name, messages, user_message):
        yield chunk


async def stream_chat(user_message: str, force_tier: int = None) -> AsyncIterator[dict[str, Any]]:
    """Nexus chat flow: Router -> Tier -> Tools -> Mem0."""

    # 0. Work-agent intent: "work on X" deterministically starts/resumes a work project,
    #    so it doesn't depend on a small model reliably calling the tool.
    _work_intercept = False
    _wl = user_message.lower().strip()
    for _pre in ("i want to work on ", "let's work on ", "lets work on ",
                 "start working on ", "work on ", "research project on "):
        if _wl.startswith(_pre):
            _work_intercept = True
            topic = user_message.strip()[len(_pre):].strip(" .?!")
            if topic:
                try:
                    from brain.work_agents import work_start, update
                    work_start(topic)
                    update(None, next_action=f"Reviewing initial research on {topic}")
                    # Autonomously kick off initial research immediately (background) so the
                    # agent starts driving toward output, not waiting passively.
                    import threading

                    def _auto(_t=topic):
                        try:
                            from brain.work_agents import work_research
                            work_research(
                                f"Give an overview of {_t}: the key sub-problems, the current "
                                f"state of the art, what is practically possible, and the main open "
                                f"gaps / unknowns to investigate next."
                            )
                            from brain.proactive import notify
                            notify(f"Initial research is in for: {_t}", "Nexus — work agent")
                        except Exception as ex:
                            logger.error("Auto research failed: %s", ex)

                    threading.Thread(target=_auto, daemon=True).start()
                except Exception as e:
                    logger.error("work_start intent failed: %s", e)
            break

    # 1. Routing
    if force_tier:
        decision = {"tier": force_tier, "confidence": 1.0, "reason": "Explicitly requested by user."}
    elif _work_intercept:
        # Project + context already created; reply fast (local, no slow tools) as the work agent.
        decision = {"tier": 1, "confidence": 1.0, "reason": "Work-agent acknowledgment."}
    else:
        decision = classify_message(user_message)

    tier = decision["tier"]

    # Auto-escalate Tier 1 to Tier 2 if message needs tools
    if tier == 1 and _needs_tools(user_message):
        tier = 2
        decision["reason"] += " (auto-escalated: tools needed)"

    model_cfg = get_model_for_tier(tier)

    yield {"type": "routing", "tier": tier, "reason": decision["reason"]}
    logger.info("Routing: Tier %d (%s)", tier, model_cfg.model_name)

    # 2. Context Building (Enhanced Memory + Skills Inject)
    # Memory search hits embeddings / Mem0 and can be slow — keep it off the event loop.
    memories = await asyncio.to_thread(get_memories_weighted, user_message)
    system_prompt = await asyncio.to_thread(build_system_prompt)

    # Skills: check if message triggers a skill, inject its prompt
    skill = match_skill(user_message)
    if skill:
        system_prompt += f"\n# Active Skill: {skill['name']}\n{skill['prompt_extension']}"
        # Auto-escalate tier if skill requires higher
        if skill["tier"] > tier:
            tier = skill["tier"]
            model_cfg = get_model_for_tier(tier)

    if memories:
        system_prompt += "\n# Relevant Background (Memory)\n" + "\n".join(f"- {m}" for m in memories)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # 3. Execution
    try:
        if model_cfg.provider == "ollama":
            # Tier 1 has no tools, Tier 2+ gets full MCP tools
            tools = mcp.get_tool_definitions() if tier >= 2 else None

            async for chunk in _run_ollama_chat(model_cfg.model_name, messages, tools, user_message):
                if chunk["type"] == "_save":
                    _persist_memory_async(chunk["user"], chunk["assistant"])
                else:
                    yield chunk

        elif model_cfg.provider == "openrouter":
            # Free smart tier — give it tools (web_search etc.); auto-falls back to local.
            from brain.openrouter_executor import run_openrouter_advisor
            or_tools = mcp.get_tool_definitions()
            async for chunk in run_openrouter_advisor(user_message, system_prompt, memories, or_tools):
                if chunk["type"] == "_save":
                    _persist_memory_async(chunk["user"], chunk["assistant"])
                else:
                    yield chunk

        elif model_cfg.provider == "anthropic":
            # Delegate to advisor_executor
            from brain.advisor_executor import run_cloud_advisor
            async for chunk in run_cloud_advisor(user_message, system_prompt, memories):
                yield chunk

    except Exception as e:
        logger.error("Chat failure: %s", e)
        yield {"type": "text", "content": f"I'm afraid I've encountered a system failure, Sir: {e}"}

    yield {"type": "done"}
