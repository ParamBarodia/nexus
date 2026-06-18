"""Tool implementations for Jarvis brain."""

import logging
import os
import subprocess
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger("jarvis.tools")

# Ollama tool definitions for native function calling
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information using DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a Windows shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Return the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def web_search(query: str) -> str:
    """Search the web using DuckDuckGo."""
    # Try duckduckgo-search library first (actual web results)
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if results:
            parts: list[str] = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                parts.append(f"{title}: {body}")
            return "\n\n".join(parts)[:2000]
    except Exception as e:
        logger.warning("DDGS search failed, falling back to Instant Answer API: %s", e)

    # Fallback: DuckDuckGo Instant Answer API
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        parts = []
        abstract = data.get("Abstract", "")
        if abstract:
            parts.append(abstract)

        for topic in data.get("RelatedTopics", [])[:5]:
            text = topic.get("Text", "")
            if text:
                parts.append(text)

        result = "\n".join(parts) if parts else "No results found."
        return result[:2000]
    except Exception as e:
        logger.error("Web search failed: %s", e)
        return f"Search failed: {e}"


def run_command(command: str) -> str:
    """Execute a Windows shell command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout or result.stderr or "(no output)"
        return output[:2000]
    except subprocess.TimeoutExpired:
        logger.warning("Command timed out: %s", command)
        return "Command failed: timed out after 15 seconds"
    except Exception as e:
        logger.error("Command failed: %s", e)
        return f"Command failed: {e}"


def get_time() -> str:
    """Return the current date and time formatted nicely."""
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


# --- External agent bridges ------------------------------------------------

HERMES_EXE = r"C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe"
UV_EXE = r"C:\Users\Admin\.local\bin\uv.exe"
COUNCIL_DIR = r"C:\Users\Admin\ai-agents"


def call_hermes(task: str) -> str:
    """Delegate a task to the local Hermes Agent (40+ tools, runs on local Ollama)."""
    try:
        exe = HERMES_EXE if os.path.exists(HERMES_EXE) else "hermes"
        result = subprocess.run(
            [exe, "-z", task],
            cwd=r"C:\Users\Admin",
            capture_output=True, text=True, timeout=300,
            encoding="utf-8", errors="replace",
        )
        out = (result.stdout or "").strip() or (result.stderr or "").strip() or "(no output)"
        return out[:4000]
    except subprocess.TimeoutExpired:
        return "Hermes timed out after 300s."
    except Exception as e:
        logger.error("call_hermes failed: %s", e)
        return f"Hermes call failed: {e}"


def council_verify(content: str) -> str:
    """Verify a claim or piece of code with the multi-model Council (returns critiques + final)."""
    try:
        exe = UV_EXE if os.path.exists(UV_EXE) else "uv"
        result = subprocess.run(
            [exe, "run", "council.py", content],
            cwd=COUNCIL_DIR,
            capture_output=True, text=True, timeout=600,
            encoding="utf-8", errors="replace",
        )
        out = (result.stdout or "").strip() or (result.stderr or "").strip() or "(no output)"
        return out[-4000:]  # the final reviewed answer is at the end
    except subprocess.TimeoutExpired:
        return "Council timed out after 600s."
    except Exception as e:
        logger.error("council_verify failed: %s", e)
        return f"Council call failed: {e}"


# Dispatch map for tool execution
TOOL_DISPATCH: dict[str, Any] = {
    "web_search": web_search,
    "run_command": run_command,
    "get_time": get_time,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name with given arguments."""
    func = TOOL_DISPATCH.get(name)
    if func is None:
        return f"Unknown tool: {name}"
    try:
        return func(**arguments)
    except Exception as e:
        logger.error("Tool %s failed: %s", name, e)
        return f"Tool {name} failed: {e}"
