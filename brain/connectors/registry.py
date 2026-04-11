"""Connector registry — discovery, lifecycle, and MCP tool aggregation."""

import importlib
import inspect
import json
import logging
import pkgutil
from pathlib import Path
from typing import Any

from brain.connectors.base import BaseConnector

logger = logging.getLogger("jarvis.connectors.registry")

STATE_FILE = Path(r"C:\jarvis\data\connectors_state.json")


class ConnectorRegistry:
    """Discovers, manages, and queries all connectors."""

    def __init__(self):
        self._available: dict[str, type[BaseConnector]] = {}
        self._active: dict[str, BaseConnector] = {}
        self._state: dict[str, dict[str, Any]] = {}
        self._load_state()

    def _load_state(self):
        """Load active-connector state from disk."""
        if STATE_FILE.exists():
            try:
                self._state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._state = {}

    def _save_state(self):
        """Persist state to disk."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def discover(self):
        """Scan brain.connectors.services for BaseConnector subclasses."""
        import brain.connectors.services as svc_pkg

        for importer, modname, ispkg in pkgutil.walk_packages(
            svc_pkg.__path__, prefix=svc_pkg.__name__ + "."
        ):
            try:
                module = importlib.import_module(modname)
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseConnector) and obj is not BaseConnector:
                        if obj.name:
                            self._available[obj.name] = obj
                            logger.debug("Discovered connector: %s", obj.name)
            except Exception as e:
                logger.warning("Failed to import connector module %s: %s", modname, e)

        # Auto-activate previously enabled connectors
        for name in list(self._state.keys()):
            if name in self._available and self._state[name].get("enabled"):
                try:
                    self._active[name] = self._available[name]()
                    logger.info("Auto-activated connector: %s", name)
                except Exception as e:
                    logger.error("Failed to activate %s: %s", name, e)

        logger.info(
            "Discovery complete: %d available, %d active",
            len(self._available),
            len(self._active),
        )

    def list_available(self) -> list[dict]:
        """Return metadata for all discovered connectors."""
        result = []
        for name, cls in sorted(self._available.items()):
            is_stub = False
            try:
                # Check if fetch raises NotImplementedError (stub detection)
                import ast
                source = inspect.getsource(cls.fetch)
                is_stub = "NotImplementedError" in source
            except Exception:
                pass

            result.append({
                "name": name,
                "description": cls.description,
                "category": cls.category,
                "poll_interval_minutes": cls.poll_interval_minutes,
                "required_env": cls.required_env,
                "status": "active" if name in self._active else ("stub" if is_stub else "available"),
            })
        return result

    def list_active(self) -> list[dict]:
        """Return metadata for active connectors."""
        return [
            {"name": c.name, "description": c.description, "category": c.category}
            for c in self._active.values()
        ]

    def get(self, name: str) -> BaseConnector | None:
        """Get an active connector instance by name."""
        return self._active.get(name)

    def install(self, name: str, creds: dict[str, str] | None = None) -> dict:
        """Enable a connector. Optionally provide credentials."""
        if name not in self._available:
            return {"ok": False, "error": f"Unknown connector: {name}"}

        # Store credentials if provided
        if creds:
            from brain.connectors.auth import store_credential
            for key, value in creds.items():
                store_credential(name, key, value)

        try:
            instance = self._available[name]()
            self._active[name] = instance
            self._state[name] = {"enabled": True}
            self._save_state()
            logger.info("Installed connector: %s", name)
            return {"ok": True, "name": name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def uninstall(self, name: str) -> dict:
        """Disable a connector."""
        if name in self._active:
            del self._active[name]
        self._state.pop(name, None)
        self._save_state()
        logger.info("Uninstalled connector: %s", name)
        return {"ok": True, "name": name}

    def get_all_mcp_tools(self) -> list[dict]:
        """Aggregate MCP tool definitions from all active connectors."""
        tools = []
        for connector in self._active.values():
            try:
                tools.extend(connector.get_mcp_tools())
            except Exception as e:
                logger.error("Failed to get tools from %s: %s", connector.name, e)
        return tools

    async def fetch_all(self) -> dict[str, dict]:
        """Fetch data from all active connectors concurrently."""
        import asyncio

        async def _fetch_one(c: BaseConnector) -> tuple[str, dict]:
            return c.name, await c.safe_fetch()

        tasks = [_fetch_one(c) for c in self._active.values()]
        results = await asyncio.gather(*tasks)
        return dict(results)

    async def close_all(self):
        """Shut down all active connectors."""
        for connector in self._active.values():
            await connector.close()
