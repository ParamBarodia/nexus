"""Life-domain tracker — Param's four fronts (research / job_hunt / phd / content).

A small persistent store JARVIS reads and updates so it always knows the single
next action per domain, with staleness + overdue computed on the fly. Fights
decision-paralysis by surfacing 'what to do next' instead of options.
"""

import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger("jarvis.domains")

DOMAINS_PATH = Path(r"C:\jarvis\data\domains.json")
LOCAL_PATH = DOMAINS_PATH.with_suffix(".local.json")  # gitignored personal override
LABELS = {"research": "Research", "job_hunt": "Job Hunt", "phd": "PhD", "content": "Content"}


def _active_path() -> Path:
    """Use the gitignored domains.local.json if present, else the tracked template."""
    return LOCAL_PATH if LOCAL_PATH.exists() else DOMAINS_PATH


def _load() -> dict:
    try:
        d = json.loads(_active_path().read_text(encoding="utf-8"))
        d.pop("_meta", None)  # drop template metadata if present
        return d
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load domains: %s", e)
        return {}


def _save(d: dict) -> None:
    # Always write to the personal .local file so the shipped template stays clean.
    LOCAL_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")


def _days_since(iso: str | None):
    if not iso:
        return None
    try:
        return (date.today() - date.fromisoformat(iso[:10])).days
    except (ValueError, TypeError):
        return None


def get_domains() -> dict:
    """All domains with computed `days_stale` and `overdue` flags."""
    out = {}
    for k, v in _load().items():
        v = dict(v)
        v["days_stale"] = _days_since(v.get("last_updated"))
        dl_days = _days_since(v.get("deadline"))
        v["overdue"] = dl_days is not None and dl_days > 0
        v["days_overdue"] = dl_days if (dl_days is not None and dl_days > 0) else 0
        v["label"] = LABELS.get(k, k.replace("_", " ").title())
        out[k] = v
    return out


def get_domain(name: str):
    return get_domains().get(name)


def update_domain(name: str, next_action: str = None, deadline: str = None,
                  notes: str = None, status: str = None) -> dict:
    """Update a domain's fields and stamp last_updated to today."""
    d = _load()
    if name not in d:
        d[name] = {"next_action": "", "deadline": None, "notes": "", "status": "active"}
    if next_action is not None:
        d[name]["next_action"] = next_action
    if deadline is not None:
        d[name]["deadline"] = deadline or None
    if notes is not None:
        d[name]["notes"] = notes
    if status is not None:
        d[name]["status"] = status
    d[name]["last_updated"] = date.today().isoformat()
    _save(d)
    logger.info("Domain '%s' updated.", name)
    return get_domains().get(name)


def summary() -> str:
    """Compact text block for the system prompt / briefing."""
    ds = get_domains()
    if not ds:
        return ""
    lines = []
    for k, v in ds.items():
        flags = []
        if v.get("overdue"):
            flags.append(f"OVERDUE {v['days_overdue']}d")
        elif v.get("days_stale") is not None and v["days_stale"] > 7:
            flags.append(f"{v['days_stale']}d stale")
        flag = f"  [{', '.join(flags)}]" if flags else ""
        lines.append(f"- {v['label']}: {v.get('next_action', '(none)')}{flag}")
    return "\n".join(lines)


def overdue_domains() -> dict:
    """Domains whose deadline has passed — used by the proactive nudge."""
    return {k: v for k, v in get_domains().items() if v.get("overdue")}
