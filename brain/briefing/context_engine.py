"""Context engine — prefetch connector data and compose daily briefings."""

import logging
from datetime import datetime
from pathlib import Path

import ollama

logger = logging.getLogger("jarvis.briefing.context_engine")

BRIEFING_DIR = Path(r"C:\jarvis\data\briefings")
BRIEFING_DIR.mkdir(parents=True, exist_ok=True)

NARRATIVE_PROMPT = """\
You are JARVIS, an AI assistant speaking to Sir (your principal, Param).
Compose a natural, conversational morning briefing as flowing prose — NOT bullet lists.
Open with the date and a brief greeting. Then LEAD with what Param should DO today across
his four fronts (Research, Job Hunt, PhD, Content) using the PRIORITIES below — name the
single next action per front, and call out anything OVERDUE first. After the priorities,
weave in any noteworthy source data (new papers, world/markets/weather). Close with one
crisp forward-looking remark. Be the steady hand: surface decisions, not menus.

--- TODAY'S PRIORITIES (Param's live domains) ---
{domains}

--- SOURCE DATA ---
{source_data}

--- REMEMBERED CONTEXT ---
{memories}

Compose the briefing now.
"""


async def prefetch_all(registry) -> dict:
    """Concurrently fetch data from every active connector."""
    logger.info("Prefetching data from all active connectors...")
    data = await registry.fetch_all()
    logger.info("Prefetch complete — %d connectors returned data.", len(data))
    return data


async def compose_briefing(prefetched: dict, memories: list) -> str:
    """Send connector summaries to the local LLM and produce a briefing."""
    # Format source data
    source_sections = []
    for name, payload in prefetched.items():
        if payload and not payload.get("error"):
            source_sections.append(f"[{name}]\n{_summarise_payload(payload)}")

    source_data = "\n\n".join(source_sections) if source_sections else "No connector data available today."

    # Format memories
    memory_text = "\n".join(
        f"- {m.get('memory', m) if isinstance(m, dict) else str(m)}"
        for m in memories
    ) if memories else "No prior memories loaded."

    # Live life-domain priorities (next action per front, overdue flagged)
    try:
        from brain.domains import summary as _domain_summary
        domains_text = _domain_summary() or "No domains tracked."
    except Exception:
        domains_text = "No domains tracked."

    prompt = NARRATIVE_PROMPT.format(domains=domains_text, source_data=source_data, memories=memory_text)

    logger.info("Sending briefing prompt to hermes3:8b (%d chars)...", len(prompt))
    try:
        response = ollama.chat(
            model="hermes3:8b",
            messages=[{"role": "user", "content": prompt}],
        )
        briefing_text = response["message"]["content"]
    except Exception as e:
        logger.error("LLM briefing generation failed: %s", e)
        briefing_text = (
            f"Good morning, Sir. Today is {datetime.now().strftime('%A, %B %d, %Y')}.\n\n"
            "I was unable to generate the full briefing due to an LLM error. "
            "Here is the raw connector data I collected:\n\n"
            + source_data
        )

    # Persist to disk
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = BRIEFING_DIR / f"{today}.md"
    filepath.write_text(briefing_text, encoding="utf-8")
    logger.info("Briefing saved to %s", filepath)

    return briefing_text


def get_todays_briefing() -> str | None:
    """Read today's briefing file if it exists, else None."""
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = BRIEFING_DIR / f"{today}.md"
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return None


def _summarise_payload(payload: dict) -> str:
    """Flatten a connector payload dict into readable text."""
    lines = []
    for key, value in payload.items():
        if isinstance(value, list):
            for item in value[:10]:  # cap items to avoid prompt bloat
                lines.append(f"  {key}: {item}")
        else:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)
