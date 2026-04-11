"""Air quality connector — AQI data from aqicn.org (World Air Quality Index)."""

import os
import logging

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.waqi_airquality")

WAQI_BASE = "https://api.waqi.info"


class WAQIAirQualityConnector(BaseConnector):
    name = "waqi_airquality"
    description = "Air quality index from aqicn.org / WAQI"
    category = "environmental"
    poll_interval_minutes = 360
    required_env = ["WAQI_API_KEY"]

    def _get_api_key(self) -> str:
        key = os.getenv("WAQI_API_KEY") or get_credential("waqi", "api_key")
        if not key:
            raise RuntimeError(
                "WAQI API key not configured. "
                "Set WAQI_API_KEY env var or store via auth.store_credential('waqi', 'api_key', ...)."
            )
        return key

    async def fetch(self, params=None):
        params = params or {}
        city = params.get("city", os.getenv("AQI_CITY", "Mumbai"))

        cache_key = f"waqi_{city}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            api_key = self._get_api_key()
        except RuntimeError as e:
            return {"error": str(e), "city": city}

        http = await self._get_http()

        try:
            resp = await http.get(f"{WAQI_BASE}/feed/{city}/", params={"token": api_key})
            resp.raise_for_status()
            raw = resp.json()

            if raw.get("status") != "ok":
                return {"error": raw.get("data", "Unknown WAQI error"), "city": city}

            d = raw["data"]
            iaqi = d.get("iaqi", {})
            data = {
                "city": d.get("city", {}).get("name", city),
                "aqi": d.get("aqi", 0),
                "dominant_pollutant": d.get("dominentpol", ""),
                "pm25": iaqi.get("pm25", {}).get("v", None),
                "pm10": iaqi.get("pm10", {}).get("v", None),
                "o3": iaqi.get("o3", {}).get("v", None),
                "no2": iaqi.get("no2", {}).get("v", None),
                "time": d.get("time", {}).get("s", ""),
            }
            self._cache_set(cache_key, data)
        except Exception as e:
            logger.error("WAQI API error: %s", e)
            data = {"error": str(e), "city": city}

        return data

    def _aqi_label(self, aqi: int) -> str:
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Moderate"
        elif aqi <= 150:
            return "Unhealthy for Sensitive"
        elif aqi <= 200:
            return "Unhealthy"
        elif aqi <= 300:
            return "Very Unhealthy"
        return "Hazardous"

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return f"Air Quality: {data['error']}"
        aqi = data.get("aqi", 0)
        label = self._aqi_label(aqi) if isinstance(aqi, int) else "Unknown"
        parts = [f"Air Quality in {data.get('city', '')}: AQI {aqi} ({label})"]
        if data.get("pm25") is not None:
            parts.append(f"PM2.5: {data['pm25']}")
        if data.get("pm10") is not None:
            parts.append(f"PM10: {data['pm10']}")
        if data.get("dominant_pollutant"):
            parts.append(f"Dominant: {data['dominant_pollutant']}")
        return " | ".join(parts)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "air_quality",
                "description": "Get air quality index (AQI) for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string", "description": "City name (default: from env)"}},
                },
                "handler": lambda city="", **kw: _sync_fetch(
                    self, {"city": city} if city else {}
                ),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
