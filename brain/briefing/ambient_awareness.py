"""Ambient awareness — continuous monitoring for alert-worthy conditions."""

import logging
from datetime import datetime

import apprise

from brain.events import bus, Event

logger = logging.getLogger("jarvis.briefing.ambient")

# Thresholds for alert conditions
ALERT_RULES = {
    "earthquake": lambda data: any(
        float(q.get("magnitude", 0)) >= 5.0
        for q in (data.get("quakes") or data.get("events") or [])
        if isinstance(q, dict)
    ),
    "crypto": lambda data: any(
        abs(float(c.get("change_24h", 0))) >= 5.0
        for c in (data.get("prices") or data.get("coins") or [])
        if isinstance(c, dict)
    ),
    "weather_alert": lambda data: bool(
        data.get("alerts") or data.get("warnings")
    ),
    "news_breaking": lambda data: any(
        item.get("breaking", False)
        for item in (data.get("articles") or data.get("items") or [])
        if isinstance(item, dict)
    ),
}

# Map connector categories to alert rule keys
CATEGORY_RULE_MAP = {
    "earthquake": "earthquake",
    "seismic": "earthquake",
    "crypto": "crypto",
    "weather": "weather_alert",
    "news": "news_breaking",
}


class AmbientMonitor:
    """Periodically checks active connectors for alert-worthy conditions."""

    def __init__(self, registry):
        self.registry = registry

    async def check_all(self) -> list[dict]:
        """Run through active connectors and fire alerts when thresholds are breached."""
        alerts_fired = []
        data = await self.registry.fetch_all()

        for connector_name, payload in data.items():
            if not payload or payload.get("error"):
                continue

            connector = self.registry.get(connector_name)
            if not connector:
                continue

            # Determine which alert rules apply based on connector category/name
            applicable_rules = self._get_applicable_rules(connector)

            for rule_name, check_fn in applicable_rules:
                try:
                    if check_fn(payload):
                        alert = {
                            "connector": connector_name,
                            "rule": rule_name,
                            "timestamp": datetime.now().isoformat(),
                            "summary": self._build_summary(rule_name, connector_name, payload),
                        }
                        alerts_fired.append(alert)

                        # Publish to event bus
                        bus.publish(Event("ambient_alert", alert))
                        logger.warning("Ambient alert: [%s] %s", rule_name, alert["summary"])

                        # Windows toast via apprise
                        self._send_toast(alert)

                except Exception as e:
                    logger.error(
                        "Alert rule '%s' failed for connector '%s': %s",
                        rule_name, connector_name, e,
                    )

        if not alerts_fired:
            logger.debug("Ambient check complete — no alerts.")

        return alerts_fired

    def _get_applicable_rules(self, connector) -> list[tuple[str, callable]]:
        """Determine which alert rules apply to a given connector."""
        rules = []
        category = getattr(connector, "category", "").lower()
        name = getattr(connector, "name", "").lower()

        for keyword, rule_key in CATEGORY_RULE_MAP.items():
            if keyword in category or keyword in name:
                if rule_key in ALERT_RULES:
                    rules.append((rule_key, ALERT_RULES[rule_key]))

        return rules

    @staticmethod
    def _build_summary(rule_name: str, connector_name: str, payload: dict) -> str:
        """Build a human-readable alert summary."""
        summaries = {
            "earthquake": "Significant earthquake detected (M5.0+)",
            "crypto": "Major crypto price movement (>5% in 24h)",
            "weather_alert": "Weather alert or warning issued",
            "news_breaking": "Breaking news detected",
        }
        base = summaries.get(rule_name, f"Alert triggered: {rule_name}")
        return f"{base} via {connector_name}"

    @staticmethod
    def _send_toast(alert: dict):
        """Send a Windows toast notification via apprise."""
        try:
            apobj = apprise.Apprise()
            apobj.add("windows://")
            apobj.notify(
                title=f"Nexus Alert: {alert['rule'].replace('_', ' ').title()}",
                body=alert["summary"],
            )
        except Exception as e:
            logger.error("Failed to send toast notification: %s", e)
