"""OpenWeatherMap connector — current weather and forecast via OpenWeatherMap API."""

import os
import logging

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.openweathermap")

OWM_BASE = "https://api.openweathermap.org/data/2.5"


class OpenWeatherMapConnector(BaseConnector):
    name = "openweathermap"
    description = "OpenWeatherMap — current weather and 5-day forecast"
    category = "environmental"
    poll_interval_minutes = 60
    required_env = ["OPENWEATHERMAP_API_KEY"]

    def _get_api_key(self) -> str:
        key = os.getenv("OPENWEATHERMAP_API_KEY") or get_credential("openweathermap", "api_key")
        if not key:
            raise RuntimeError(
                "OpenWeatherMap API key not configured. "
                "Set OPENWEATHERMAP_API_KEY env var or store via auth.store_credential."
            )
        return key

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "current")
        city = params.get("city", os.getenv("WEATHER_CITY", "Mumbai"))
        units = params.get("units", "metric")

        cache_key = f"owm_{action}_{city}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            api_key = self._get_api_key()
        except RuntimeError as e:
            return {"error": str(e), "action": action}

        http = await self._get_http()

        try:
            if action == "forecast":
                resp = await http.get(
                    f"{OWM_BASE}/forecast",
                    params={"q": city, "appid": api_key, "units": units, "cnt": 8},
                )
                resp.raise_for_status()
                raw = resp.json()
                forecasts = []
                for item in raw.get("list", []):
                    forecasts.append({
                        "dt_txt": item.get("dt_txt", ""),
                        "temp": item["main"]["temp"],
                        "description": item["weather"][0]["description"] if item.get("weather") else "",
                        "humidity": item["main"].get("humidity", 0),
                        "wind_speed": item.get("wind", {}).get("speed", 0),
                    })
                data = {"action": "forecast", "city": city, "forecasts": forecasts}
            else:
                # current
                resp = await http.get(
                    f"{OWM_BASE}/weather",
                    params={"q": city, "appid": api_key, "units": units},
                )
                resp.raise_for_status()
                raw = resp.json()
                data = {
                    "action": "current",
                    "city": raw.get("name", city),
                    "temp": raw["main"]["temp"],
                    "feels_like": raw["main"]["feels_like"],
                    "description": raw["weather"][0]["description"] if raw.get("weather") else "",
                    "humidity": raw["main"].get("humidity", 0),
                    "wind_speed": raw.get("wind", {}).get("speed", 0),
                }

            self._cache_set(cache_key, data)
        except Exception as e:
            logger.error("OpenWeatherMap API error: %s", e)
            data = {"error": str(e), "action": action, "city": city}

        return data

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return f"Weather: {data['error']}"
        if data.get("action") == "forecast":
            forecasts = data.get("forecasts", [])
            if not forecasts:
                return f"No forecast data for {data.get('city', '')}."
            lines = [f"Forecast for {data.get('city', '')}:"]
            for f_ in forecasts[:6]:
                lines.append(f"  - {f_['dt_txt']}: {f_['temp']}C, {f_['description']}")
            return "\n".join(lines)
        else:
            return (
                f"Weather in {data.get('city', '')}: {data.get('temp', '')}C "
                f"(feels {data.get('feels_like', '')}C), {data.get('description', '')}, "
                f"humidity {data.get('humidity', '')}%, wind {data.get('wind_speed', '')} m/s"
            )

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "weather_current",
                "description": "Get current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string", "description": "City name (default: from env)"}},
                },
                "handler": lambda city="", **kw: _sync_fetch(
                    self, {"action": "current", **({"city": city} if city else {})}
                ),
            },
            {
                "name": "weather_forecast",
                "description": "Get weather forecast for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string", "description": "City name (default: from env)"}},
                },
                "handler": lambda city="", **kw: _sync_fetch(
                    self, {"action": "forecast", **({"city": city} if city else {})}
                ),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
