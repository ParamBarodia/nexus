"""Proactive triggers and notifications."""

import logging
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import apprise
from brain.projects import get_active
from brain.memory_mem0 import get_memories

logger = logging.getLogger("jarvis.proactive")

# Setup dedicated log
PROACTIVE_LOG = r"C:\jarvis\logs\proactive.log"
p_logger = logging.getLogger("jarvis.proactive_file")
fh = logging.FileHandler(PROACTIVE_LOG, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
p_logger.addHandler(fh)
p_logger.setLevel(logging.INFO)

scheduler = AsyncIOScheduler()

# --- Lazy-loaded singletons for briefing subsystem ---
_registry = None
_ambient_monitor = None


def _get_registry():
    """Return (or create) the shared ConnectorRegistry instance."""
    global _registry
    if _registry is None:
        from brain.connectors.registry import ConnectorRegistry
        _registry = ConnectorRegistry()
        _registry.discover()
    return _registry


def _get_ambient_monitor():
    """Return (or create) the shared AmbientMonitor instance."""
    global _ambient_monitor
    if _ambient_monitor is None:
        from brain.briefing.ambient_awareness import AmbientMonitor
        _ambient_monitor = AmbientMonitor(_get_registry())
    return _ambient_monitor


def notify(message: str, title: str = "Nexus Briefing"):
    """Send notification via Apprise (ntfy.sh by default)."""
    topic = os.getenv("NTFY_TOPIC", "nexus-param")
    apobj = apprise.Apprise()
    apobj.add(f"ntfy://{topic}")
    apobj.notify(
        body=message,
        title=title,
    )
    p_logger.info("Notification sent: %s", title)


async def prefetch_and_brief():
    """7:30 AM job — prefetch all connectors then compose the morning briefing."""
    from brain.briefing.context_engine import prefetch_all, compose_briefing
    p_logger.info("Running prefetch + briefing composition...")
    try:
        registry = _get_registry()
        prefetched = await prefetch_all(registry)
        memories = get_memories("daily briefing context", limit=10)
        await compose_briefing(prefetched, memories)
        p_logger.info("Prefetch + briefing composition complete.")
    except Exception as e:
        p_logger.error("Prefetch/briefing failed: %s", e)


async def morning_briefing():
    """8:00 AM job — read today's composed briefing and send notification."""
    from brain.briefing.context_engine import get_todays_briefing
    p_logger.info("Executing morning briefing...")

    briefing = get_todays_briefing()
    if briefing:
        # Truncate for notification if very long
        notify_text = briefing if len(briefing) < 2000 else briefing[:1997] + "..."
        notify(notify_text, "Morning Briefing")
    else:
        # Fallback to basic briefing if composition hasn't run
        active = get_active()
        proj_name = active["name"] if active else "No active project"
        fallback = f"Good morning, Sir. Today is {datetime.now().strftime('%A, %B %d')}.\n"
        fallback += f"Active project: {proj_name}\n"
        fallback += "Systems are nominal. Awaiting your instructions."
        notify(fallback, "Morning Briefing")


async def evening_reflection():
    """9:00 PM job — compose and send the evening reflection."""
    from brain.briefing.evening_synthesis import compose_reflection
    p_logger.info("Executing evening reflection...")
    try:
        registry = _get_registry()
        reflection = await compose_reflection(registry)
        notify_text = reflection if len(reflection) < 2000 else reflection[:1997] + "..."
        notify(notify_text, "Evening Reflection")
    except Exception as e:
        p_logger.error("Evening reflection failed: %s", e)
        notify("Good evening, Sir. Would you like to review today's progress?", "Evening Reflection")


async def ambient_check():
    """Every-15-minute job — scan connectors for alert-worthy conditions."""
    p_logger.info("Running ambient awareness check...")
    try:
        monitor = _get_ambient_monitor()
        alerts = await monitor.check_all()
        if alerts:
            p_logger.info("Ambient check fired %d alert(s).", len(alerts))
        else:
            p_logger.debug("Ambient check — all clear.")
    except Exception as e:
        p_logger.error("Ambient check failed: %s", e)


async def daily_backup():
    """Automated daily backup at 3 AM."""
    from brain.backup import backup_all
    try:
        result = backup_all()
        p_logger.info("Daily backup: %s", result)
    except Exception as e:
        p_logger.error("Daily backup failed: %s", e)


async def weekly_export():
    """Automated weekly markdown export at Sunday midnight."""
    from brain.backup import export_human_readable
    try:
        result = export_human_readable()
        p_logger.info("Weekly export: %s", result)
    except Exception as e:
        p_logger.error("Weekly export failed: %s", e)


def start_scheduler():
    # 7:30 AM — prefetch connectors + compose briefing via LLM
    scheduler.add_job(prefetch_and_brief, 'cron', hour=7, minute=30)
    # 8:00 AM — send the composed briefing as notification
    scheduler.add_job(morning_briefing, 'cron', hour=8, minute=0)
    # 9:00 PM — evening reflection
    scheduler.add_job(evening_reflection, 'cron', hour=21, minute=0)
    # Every 15 minutes — ambient awareness check
    scheduler.add_job(ambient_check, 'interval', minutes=15)
    # 3:00 AM — daily backup
    scheduler.add_job(daily_backup, 'cron', hour=3, minute=0)
    # Sunday midnight — weekly export
    scheduler.add_job(weekly_export, 'cron', day_of_week='sun', hour=0, minute=0)

    scheduler.start()
    logger.info("Proactive scheduler started (briefings + ambient + backups).")
