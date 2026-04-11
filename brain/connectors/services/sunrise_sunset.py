"""Sunrise/Sunset connector — sunrise-sunset.org API (free, no auth)."""

import os

from brain.connectors.base import BaseConnector


class SunriseSunsetConnector(BaseConnector):
    name = "sunrise_sunset"
    description = "Sunrise and sunset times for your location"
    category = "environmental"
    poll_interval_minutes = 0  # on-demand
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        lat = params.get("lat") or os.getenv("HOME_LAT", "23.0225")
        lon = params.get("lon") or os.getenv("HOME_LON", "72.5714")

        http = await self._get_http()
        resp = await http.get(
            "https://api.sunrise-sunset.org/json",
            params={"lat": lat, "lng": lon, "formatted": 0},
        )
        resp.raise_for_status()
        data = resp.json().get("results", {})
        return {
            "sunrise": data.get("sunrise", ""),
            "sunset": data.get("sunset", ""),
            "solar_noon": data.get("solar_noon", ""),
            "day_length": data.get("day_length", 0),
            "lat": lat,
            "lon": lon,
        }

    def briefing_summary(self, data: dict) -> str:
        return f"Sunrise: {data.get('sunrise', 'N/A')}, Sunset: {data.get('sunset', 'N/A')}"

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "sunrise_sunset",
                "description": "Get sunrise and sunset times. Optional: lat, lon.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "string", "description": "Latitude"},
                        "lon": {"type": "string", "description": "Longitude"},
                    },
                },
                "handler": lambda lat=None, lon=None, **kw: _sync(self, lat, lon),
            }
        ]


def _sync(connector, lat, lon):
    import asyncio
    params = {}
    if lat:
        params["lat"] = lat
    if lon:
        params["lon"] = lon
    data = asyncio.run(connector.fetch(params))
    return f"Sunrise: {data['sunrise']}, Sunset: {data['sunset']}, Day length: {data['day_length']}s"
