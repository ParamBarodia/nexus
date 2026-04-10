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

async def morning_briefing():
    """Generate and send morning briefing."""
    p_logger.info("Executing morning briefing...")
    active = get_active()
    proj_name = active["name"] if active else "No active project"
    
    # In a real scenario, we'd trigger an LLM call here. 
    # For now, we'll use a placeholder logic that would be called by the LLM.
    briefing = f"Good morning, Sir. Today is {datetime.now().strftime('%A, %B %d')}.\n"
    briefing += f"Active project: {proj_name}\n"
    briefing += "Systems are nominal. Awaiting your instructions."
    
    notify(briefing, "Morning Briefing")

async def evening_reflection():
    """Prompt for evening reflection."""
    p_logger.info("Executing evening reflection...")
    notify("Good evening, Sir. Would you like to review today's progress?", "Evening Reflection")

def start_scheduler():
    # Morning briefing at 8:00 AM
    scheduler.add_job(morning_briefing, 'cron', hour=8, minute=0)
    # Evening reflection at 9:00 PM
    scheduler.add_job(evening_reflection, 'cron', hour=21, minute=0)
    
    scheduler.start()
    logger.info("Proactive scheduler started.")
