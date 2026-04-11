"""Abstract base class for all Nexus connectors."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger("jarvis.connectors")


class BaseConnector(ABC):
    """Base class every connector must extend.

    Provides built-in caching (TTL), rate limiting, error isolation,
    and automatic MCP tool registration.
    """

    name: str = ""
    description: str = ""
    category: str = ""  # personal, environmental, news, markets, sports, dev
    poll_interval_minutes: int = 0  # 0 = on-demand only
    required_env: list[str] = []

    # Internal caching
    _cache: dict[str, Any] = {}
    _cache_ts: dict[str, float] = {}
    _cache_ttl: int = 300  # seconds

    def __init__(self):
        self._http: httpx.AsyncClient | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        """Lazy-init a shared async HTTP client."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    def _cache_get(self, key: str) -> Any | None:
        """Return cached value if still fresh, else None."""
        ts = self._cache_ts.get(key, 0)
        if time.time() - ts < self._cache_ttl:
            return self._cache.get(key)
        return None

    def _cache_set(self, key: str, value: Any):
        """Store a value in the cache."""
        self._cache[key] = value
        self._cache_ts[key] = time.time()

    @abstractmethod
    async def fetch(self, params: dict | None = None) -> dict:
        """Fetch data from the source. Must be implemented by each connector."""
        ...

    @abstractmethod
    def briefing_summary(self, data: dict) -> str:
        """Return a human-readable summary for briefing composition."""
        ...

    async def health_check(self) -> dict:
        """Check if the connector is healthy and reachable."""
        try:
            result = await asyncio.wait_for(self.fetch(), timeout=15.0)
            return {"healthy": True, "message": "OK", "sample_keys": list(result.keys())[:5]}
        except Exception as e:
            return {"healthy": False, "message": str(e)}

    def get_mcp_tools(self) -> list[dict]:
        """Return MCP tool definitions for this connector.

        Override in subclass to expose tools. Default returns empty list.
        """
        return []

    async def safe_fetch(self, params: dict | None = None) -> dict:
        """Fetch with error isolation — never raises, returns error dict instead."""
        try:
            return await self.fetch(params)
        except Exception as e:
            logger.error("Connector %s fetch failed: %s", self.name, e)
            return {"error": str(e), "connector": self.name}

    async def close(self):
        """Clean up resources."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
