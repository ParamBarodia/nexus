"""Google Maps traffic connector — commute time and traffic via Google Maps Directions API."""

import os
import logging

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.google_maps_traffic")

MAPS_BASE = "https://maps.googleapis.com/maps/api/directions/json"


class GoogleMapsTrafficConnector(BaseConnector):
    name = "google_maps_traffic"
    description = "Google Maps — commute time and traffic conditions"
    category = "environmental"
    poll_interval_minutes = 30
    required_env = ["GOOGLE_MAPS_API_KEY"]

    def _get_api_key(self) -> str:
        key = os.getenv("GOOGLE_MAPS_API_KEY") or get_credential("google_maps", "api_key")
        if not key:
            raise RuntimeError(
                "Google Maps API key not configured. "
                "Set GOOGLE_MAPS_API_KEY env var or store via auth.store_credential('google_maps', 'api_key', ...)."
            )
        return key

    async def fetch(self, params=None):
        params = params or {}
        origin = params.get("origin", os.getenv("COMMUTE_ORIGIN", ""))
        destination = params.get("destination", os.getenv("COMMUTE_DESTINATION", ""))

        if not origin or not destination:
            return {
                "error": "Origin and destination required. Set COMMUTE_ORIGIN and COMMUTE_DESTINATION env vars.",
                "origin": origin,
                "destination": destination,
            }

        cache_key = f"traffic_{origin}_{destination}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            api_key = self._get_api_key()
        except RuntimeError as e:
            return {"error": str(e)}

        http = await self._get_http()

        try:
            resp = await http.get(
                MAPS_BASE,
                params={
                    "origin": origin,
                    "destination": destination,
                    "departure_time": "now",
                    "traffic_model": "best_guess",
                    "key": api_key,
                },
            )
            resp.raise_for_status()
            raw = resp.json()

            if raw.get("status") != "OK":
                return {"error": f"Directions API: {raw.get('status')}", "origin": origin, "destination": destination}

            route = raw["routes"][0]
            leg = route["legs"][0]
            data = {
                "origin": leg.get("start_address", origin),
                "destination": leg.get("end_address", destination),
                "distance": leg.get("distance", {}).get("text", ""),
                "duration": leg.get("duration", {}).get("text", ""),
                "duration_in_traffic": leg.get("duration_in_traffic", {}).get("text", ""),
                "duration_seconds": leg.get("duration", {}).get("value", 0),
                "traffic_seconds": leg.get("duration_in_traffic", {}).get("value", 0),
                "summary": route.get("summary", ""),
            }
            self._cache_set(cache_key, data)
        except Exception as e:
            logger.error("Google Maps API error: %s", e)
            data = {"error": str(e), "origin": origin, "destination": destination}

        return data

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return f"Traffic: {data['error']}"
        normal = data.get("duration", "")
        traffic = data.get("duration_in_traffic", "")
        traffic_str = f" (in traffic: {traffic})" if traffic and traffic != normal else ""
        return (
            f"Commute {data.get('origin', '')} -> {data.get('destination', '')}: "
            f"{normal}{traffic_str}, {data.get('distance', '')} via {data.get('summary', '')}"
        )

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "traffic_commute",
                "description": "Get commute time with live traffic between two locations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string", "description": "Starting address or place"},
                        "destination": {"type": "string", "description": "Destination address or place"},
                    },
                },
                "handler": lambda origin="", destination="", **kw: _sync_fetch(
                    self, {
                        **({"origin": origin} if origin else {}),
                        **({"destination": destination} if destination else {}),
                    }
                ),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
