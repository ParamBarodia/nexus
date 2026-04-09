"""Ollama integration and streaming chat for Jarvis brain."""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import ollama

from brain.memory import append, get_recent
from brain.prompt import build_system_prompt
from brain.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger("jarvis.chat")

MODEL = "gemma4:e4b"


async def stream_chat(user_message: str) -> AsyncIterator[dict[str, Any]]:
    """Stream a chat response, handling tool calls as they arise."""
    # Save user message to memory
    append("user", user_message)

    # Build messages: system + recent memory + current message
    system_prompt = build_system_prompt()
    history = get_recent(n=20)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]
    # Add history (excluding the last user message since we add it explicitly)
    if history and history[-1]["role"] == "user" and history[-1]["content"] == user_message:
        messages.extend(history[:-1])
    else:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # First call — with tools, non-streaming (need to check for tool calls)
    try:
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            stream=False,
        )
    except Exception as e:
        logger.error("Ollama chat failed: %s", e)
        error_msg = f"I'm afraid I encountered a system error, Sir: {e}"
        append("assistant", error_msg)
        yield {"type": "text", "content": error_msg}
        yield {"type": "done"}
        return

    message = response.get("message", {})
    tool_calls = message.get("tool_calls", None)

    # Handle tool calls if present
    if tool_calls:
        messages.append(message)

        for tc in tool_calls:
            func_info = tc.get("function", {})
            tool_name = func_info.get("name", "unknown")
            tool_args = func_info.get("arguments", {})

            logger.info("Tool call: %s(%s)", tool_name, json.dumps(tool_args))
            yield {"type": "tool_call", "tool": tool_name, "args": tool_args}

            result = execute_tool(tool_name, tool_args)
            logger.info("Tool result: %s", result[:200])
            yield {"type": "tool_result", "tool": tool_name, "result": result}

            messages.append({"role": "tool", "content": result})

        # Stream the follow-up response after tool results
        try:
            full_text = ""
            for chunk in ollama.chat(
                model=MODEL,
                messages=messages,
                stream=True,
            ):
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_text += token
                    yield {"type": "token", "content": token}

            if full_text:
                append("assistant", full_text)
                yield {"type": "done"}
                return
        except Exception as e:
            logger.error("Ollama follow-up failed: %s", e)
            error_msg = f"Tool executed, but I hit an error formulating my response, Sir: {e}"
            append("assistant", error_msg)
            yield {"type": "text", "content": error_msg}
            yield {"type": "done"}
            return
    else:
        # No tool calls — stream the response token by token
        # Re-do the call with streaming enabled
        try:
            full_text = ""
            for chunk in ollama.chat(
                model=MODEL,
                messages=messages,
                stream=True,
            ):
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_text += token
                    yield {"type": "token", "content": token}

            if full_text:
                append("assistant", full_text)
        except Exception as e:
            logger.error("Ollama streaming failed: %s", e)
            error_msg = f"System error, Sir: {e}"
            append("assistant", error_msg)
            yield {"type": "text", "content": error_msg}

    yield {"type": "done"}
