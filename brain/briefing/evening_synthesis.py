"""Evening synthesis — reflect on the day and preview tomorrow."""

import logging
from datetime import datetime
from pathlib import Path

import ollama

from brain.briefing.context_engine import get_todays_briefing

logger = logging.getLogger("jarvis.briefing.evening_synthesis")

REFLECTION_DIR = Path(r"C:\jarvis\data\reflections")
REFLECTION_DIR.mkdir(parents=True, exist_ok=True)

REFLECTION_PROMPT = """\
You are JARVIS, an AI assistant speaking to Sir (your principal).
Below is the morning briefing that was delivered today, followed by
any events or data collected throughout the day from connectors.

Compose a concise evening reflection covering three things:
1. What happened today — key developments and how they unfolded.
2. What mattered — the most significant items and why.
3. What's tomorrow — anything already on the radar for the next day.

Write in a natural, conversational tone. No bullet lists.

--- MORNING BRIEFING ---
{morning_briefing}

--- TODAY'S CONNECTOR EVENTS ---
{events}

Compose the evening reflection now.
"""


async def compose_reflection(registry) -> str:
    """Pull today's briefing + fresh connector data and produce an evening reflection."""
    # Gather inputs
    morning = get_todays_briefing() or "No morning briefing was generated today."

    logger.info("Fetching end-of-day connector data for reflection...")
    latest_data = await registry.fetch_all()

    event_sections = []
    for name, payload in latest_data.items():
        if payload and not payload.get("error"):
            event_sections.append(f"[{name}]\n{_fmt(payload)}")

    events_text = "\n\n".join(event_sections) if event_sections else "No additional events captured today."

    prompt = REFLECTION_PROMPT.format(morning_briefing=morning, events=events_text)

    logger.info("Sending reflection prompt to qwen2.5:14b (%d chars)...", len(prompt))
    try:
        response = ollama.chat(
            model="qwen2.5:14b",
            messages=[{"role": "user", "content": prompt}],
        )
        reflection_text = response["message"]["content"]
    except Exception as e:
        logger.error("LLM reflection generation failed: %s", e)
        reflection_text = (
            f"Good evening, Sir. Today is {datetime.now().strftime('%A, %B %d, %Y')}.\n\n"
            "I was unable to generate the evening reflection due to an LLM error.\n\n"
            + events_text
        )

    # Persist
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = REFLECTION_DIR / f"{today}.md"
    filepath.write_text(reflection_text, encoding="utf-8")
    logger.info("Evening reflection saved to %s", filepath)

    return reflection_text


def _fmt(payload: dict) -> str:
    """Flatten a connector payload into readable lines."""
    lines = []
    for key, value in payload.items():
        if isinstance(value, list):
            for item in value[:10]:
                lines.append(f"  {key}: {item}")
        else:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)
