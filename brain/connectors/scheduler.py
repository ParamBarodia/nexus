"""Connector polling scheduler — registers APScheduler jobs for connectors with poll intervals."""

import logging

from brain.connectors.registry import ConnectorRegistry
from brain.events import bus, Event

logger = logging.getLogger("jarvis.connectors.scheduler")


async def _poll_connector(connector_name: str, registry: ConnectorRegistry):
    """Fetch data from a connector and publish to the event bus."""
    connector = registry.get(connector_name)
    if not connector:
        return

    data = await connector.safe_fetch()
    if "error" not in data:
        bus.publish(Event("connector_data", {"connector": connector_name, "data": data}))
        logger.debug("Polled %s: %d keys", connector_name, len(data))
    else:
        logger.warning("Poll failed for %s: %s", connector_name, data.get("error"))


def register_polling_jobs(registry: ConnectorRegistry, scheduler):
    """Add APScheduler interval jobs for connectors with poll_interval_minutes > 0."""
    count = 0
    for connector in registry._active.values():
        if connector.poll_interval_minutes > 0:
            job_id = f"connector_poll_{connector.name}"

            # Remove existing job if any (re-registration safety)
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass

            scheduler.add_job(
                _poll_connector,
                "interval",
                minutes=connector.poll_interval_minutes,
                args=[connector.name, registry],
                id=job_id,
                replace_existing=True,
            )
            count += 1
            logger.info(
                "Registered polling: %s every %d min",
                connector.name,
                connector.poll_interval_minutes,
            )

    logger.info("Polling jobs registered: %d connectors", count)
