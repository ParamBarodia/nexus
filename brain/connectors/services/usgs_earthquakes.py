"""USGS Earthquakes connector — earthquake.usgs.gov API (free, no auth)."""

from brain.connectors.base import BaseConnector


class USGSEarthquakesConnector(BaseConnector):
    name = "usgs_earthquakes"
    description = "Recent significant earthquakes worldwide from USGS"
    category = "environmental"
    poll_interval_minutes = 360
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        period = params.get("period", "day")  # hour, day, week, month
        min_mag = params.get("min_magnitude", "4.5")

        http = await self._get_http()
        resp = await http.get(
            f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{min_mag}_{period}.geojson"
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
        quakes = []
        for f in features[:10]:
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [])
            quakes.append({
                "magnitude": props.get("mag"),
                "place": props.get("place", ""),
                "time": props.get("time"),
                "url": props.get("url", ""),
                "lat": coords[1] if len(coords) > 1 else None,
                "lon": coords[0] if coords else None,
            })
        return {"period": period, "min_magnitude": min_mag, "count": len(quakes), "earthquakes": quakes}

    def briefing_summary(self, data: dict) -> str:
        quakes = data.get("earthquakes", [])
        if not quakes:
            return "No significant earthquakes in the last day."
        lines = [f"{len(quakes)} recent earthquakes (M{data.get('min_magnitude', '4.5')}+):"]
        for q in quakes[:3]:
            lines.append(f"  - M{q['magnitude']} near {q['place']}")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "earthquakes_recent",
                "description": "Get recent significant earthquakes from USGS.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync(self),
            }
        ]


def _sync(connector):
    import asyncio
    data = asyncio.run(connector.fetch())
    quakes = data.get("earthquakes", [])
    if not quakes:
        return "No significant earthquakes recently."
    return "\n".join(f"M{q['magnitude']} - {q['place']}" for q in quakes)
