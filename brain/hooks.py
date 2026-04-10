"""User-definable event hooks for Nexus."""

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from brain.events import bus, Event

logger = logging.getLogger("jarvis.hooks")

HOOKS_FILE = Path(r"C:\jarvis\data\hooks.json")


def _load_hooks() -> list[dict[str, Any]]:
    if not HOOKS_FILE.exists():
        return []
    try:
        return json.loads(HOOKS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_hooks(hooks: list[dict[str, Any]]):
    HOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    HOOKS_FILE.write_text(json.dumps(hooks, indent=2), encoding="utf-8")


def add_hook(trigger: str, description: str, action: str,
             filters: dict[str, str] | None = None, enabled: bool = True) -> dict:
    """Register a new hook.

    Args:
        trigger: event type to listen for (e.g. 'file_created', 'clipboard_changed', 'user_idle')
        description: human-readable description
        action: prompt to send to chat engine when triggered
        filters: optional conditions on event payload (key: substring match on value)
        enabled: whether the hook is active
    """
    hooks = _load_hooks()
    hook = {
        "id": str(uuid.uuid4())[:8],
        "trigger": trigger,
        "description": description,
        "action": action,
        "filters": filters or {},
        "enabled": enabled,
    }
    hooks.append(hook)
    _save_hooks(hooks)
    logger.info("Hook added: %s -> %s", trigger, description)
    return hook


def remove_hook(hook_id: str) -> bool:
    hooks = _load_hooks()
    original = len(hooks)
    hooks = [h for h in hooks if h["id"] != hook_id]
    _save_hooks(hooks)
    return len(hooks) < original


def toggle_hook(hook_id: str) -> bool | None:
    hooks = _load_hooks()
    for h in hooks:
        if h["id"] == hook_id:
            h["enabled"] = not h["enabled"]
            _save_hooks(hooks)
            return h["enabled"]
    return None


def list_hooks() -> list[dict[str, Any]]:
    return _load_hooks()


def _matches_filters(event: Event, filters: dict[str, str]) -> bool:
    """Check if event payload matches hook filters."""
    for key, pattern in filters.items():
        val = str(event.payload.get(key, ""))
        if pattern.lower() not in val.lower():
            return False
    return True


def _on_event(event: Event):
    """Called for every event — checks all hooks and fires matching ones."""
    hooks = _load_hooks()
    for hook in hooks:
        if not hook.get("enabled", True):
            continue
        if hook["trigger"] != event.event_type:
            continue
        if not _matches_filters(event, hook.get("filters", {})):
            continue

        logger.info("Hook fired: %s (event: %s)", hook["description"], event.event_type)

        # Execute the hook action by sending it as a chat message
        try:
            import asyncio
            from brain.chat import stream_chat

            action_prompt = hook["action"]
            # Inject event context
            if event.payload:
                action_prompt += f"\n\n[Hook context: {json.dumps(event.payload)[:500]}]"

            async def _run():
                async for _ in stream_chat(action_prompt, force_tier=2):
                    pass  # consume the stream, results go to memory

            # Run in event loop if available, else create one
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_run())
            except RuntimeError:
                asyncio.run(_run())
        except Exception as e:
            logger.error("Hook execution failed: %s", e)


def register_event_listeners():
    """Subscribe hook handler to the global event bus."""
    bus.subscribe_all(_on_event)
    logger.info("Hook event listeners registered (%d hooks)", len(_load_hooks()))
