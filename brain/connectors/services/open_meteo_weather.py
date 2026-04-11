"""Open-Meteo weather + AQI connector — completely free, no API key, satellite/model data.
Uses open-meteo.com (WMO weather models) and air-quality API (CAMS/Copernicus satellite).
Covers India via IMD/GFS/ICON models. No rate limits for personal use.
"""

import os
from brain.connectors.base import BaseConnector


class OpenMeteoWeatherConnector(BaseConnector):
    name = "weather"
    description = "Weather + AQI from Open-Meteo (free, no API key, satellite data)"
    category = "environmental"
    poll_interval_minutes = 30
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        lat = params.get("lat") or os.getenv("HOME_LAT", "23.0225")
        lon = params.get("lon") or os.getenv("HOME_LON", "72.5714")
        action = params.get("action", "current")

        cache_key = f"ometeo_{action}_{lat}_{lon}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        http = await self._get_http()
        result = {"action": action, "lat": lat, "lon": lon}

        if action == "forecast":
            resp = await http.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum,windspeed_10m_max",
                    "timezone": "auto", "forecast_days": 5,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("daily", {})
            days = []
            times = data.get("time", [])
            for i, t in enumerate(times):
                days.append({
                    "date": t,
                    "temp_max": data.get("temperature_2m_max", [None])[i],
                    "temp_min": data.get("temperature_2m_min", [None])[i],
                    "code": data.get("weathercode", [0])[i],
                    "rain_mm": data.get("precipitation_sum", [0])[i],
                    "wind_max": data.get("windspeed_10m_max", [0])[i],
                    "description": _wmo_code(data.get("weathercode", [0])[i]),
                })
            result["forecast"] = days

        else:
            # Current weather
            resp = await http.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weathercode,windspeed_10m,winddirection_10m,pressure_msl",
                    "timezone": "auto",
                },
            )
            resp.raise_for_status()
            cur = resp.json().get("current", {})
            result["temp"] = cur.get("temperature_2m")
            result["feels_like"] = cur.get("apparent_temperature")
            result["humidity"] = cur.get("relative_humidity_2m")
            result["wind_speed"] = cur.get("windspeed_10m")
            result["wind_dir"] = cur.get("winddirection_10m")
            result["pressure"] = cur.get("pressure_msl")
            result["code"] = cur.get("weathercode", 0)
            result["description"] = _wmo_code(cur.get("weathercode", 0))

            # AQI from Open-Meteo Air Quality API (CAMS/Copernicus satellite)
            try:
                aqi_resp = await http.get(
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    params={
                        "latitude": lat, "longitude": lon,
                        "current": "european_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
                    },
                )
                aqi_resp.raise_for_status()
                aqi = aqi_resp.json().get("current", {})
                result["aqi"] = aqi.get("european_aqi")
                result["pm25"] = aqi.get("pm2_5")
                result["pm10"] = aqi.get("pm10")
                result["no2"] = aqi.get("nitrogen_dioxide")
                result["so2"] = aqi.get("sulphur_dioxide")
                result["o3"] = aqi.get("ozone")
                result["aqi_label"] = _aqi_label(aqi.get("european_aqi"))
            except Exception:
                result["aqi"] = None

        self._cache_set(cache_key, result)
        return result

    def briefing_summary(self, data: dict) -> str:
        if data.get("action") == "forecast":
            days = data.get("forecast", [])
            if not days:
                return "No forecast data."
            lines = ["Weather forecast:"]
            for d in days[:3]:
                lines.append(f"  {d['date']}: {d['temp_min']}-{d['temp_max']}C, {d['description']}")
            return "\n".join(lines)

        parts = [f"Weather: {data.get('temp')}C (feels {data.get('feels_like')}C), {data.get('description')}"]
        parts.append(f"Humidity: {data.get('humidity')}%, Wind: {data.get('wind_speed')} km/h")
        if data.get("aqi") is not None:
            parts.append(f"AQI: {data['aqi']} ({data.get('aqi_label', '')}) | PM2.5: {data.get('pm25')}")
        return "\n".join(parts)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "weather_current",
                "description": "Get current weather and AQI for your location (or specify lat/lon).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "string"}, "lon": {"type": "string"},
                    },
                },
                "handler": lambda **kw: _sync(self, {"action": "current", **{k: v for k, v in kw.items() if v}}),
            },
            {
                "name": "weather_forecast",
                "description": "Get 5-day weather forecast.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "string"}, "lon": {"type": "string"},
                    },
                },
                "handler": lambda **kw: _sync(self, {"action": "forecast", **{k: v for k, v in kw.items() if v}}),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)


def _wmo_code(code):
    """Convert WMO weather code to description."""
    codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
        55: "Dense drizzle", 56: "Freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Light freezing rain", 67: "Heavy freezing rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
        80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
    }
    return codes.get(code, f"Code {code}")


def _aqi_label(aqi):
    """European AQI to label."""
    if aqi is None: return "N/A"
    if aqi <= 20: return "Good"
    if aqi <= 40: return "Fair"
    if aqi <= 60: return "Moderate"
    if aqi <= 80: return "Poor"
    if aqi <= 100: return "Very Poor"
    return "Hazardous"
