"""Persistent per-topic WORK AGENTS.

When the user says "work on X", Nexus creates a dedicated, persistent work project that
accumulates research summaries, sources, gaps, ideas and a plan — and stays alive until
closed. JARVIS ideates WITH this accumulated context. Research sub-tasks are delegated to
Hermes (which spawns its own parallel subagents); results are appended here.

Storage mirrors the proven domains.py pattern: a JSON store with a gitignored .local override.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger("jarvis.work_agents")

WORK_PATH = Path(r"C:\jarvis\data\work_projects.json")
LOCAL_PATH = WORK_PATH.with_suffix(".local.json")  # gitignored personal data


def _active_path() -> Path:
    return LOCAL_PATH if LOCAL_PATH.exists() else WORK_PATH


def _load() -> dict:
    try:
        d = json.loads(_active_path().read_text(encoding="utf-8"))
        d.pop("_meta", None)
        return d
    except (json.JSONDecodeError, OSError):
        return {}


def _save(d: dict) -> None:
    # Always write to the personal .local file so any shipped template stays clean.
    LOCAL_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")


def _slug(topic: str) -> str:
    s = "".join(c if c.isalnum() or c in " -" else "" for c in topic.lower()).strip()
    return "-".join(s.split())[:40] or "project"


def work_start(topic: str, goal: str = "") -> dict:
    """Create (or re-activate) a persistent work project for a topic."""
    d = _load()
    pid = _slug(topic)
    if pid in d and d[pid].get("status") != "closed":
        d[pid]["last_active"] = datetime.now().isoformat()
        _save(d)
        return d[pid]
    d[pid] = {
        "id": pid,
        "topic": topic,
        "goal": goal,
        "status": "active",
        "created": date.today().isoformat(),
        "last_active": datetime.now().isoformat(),
        "summary": "",
        "sources": [],
        "gaps": [],
        "ideas": [],
        "plan": "",
        "next_action": "Run initial research on the topic",
    }
    _save(d)
    logger.info("Work project started: %s", pid)
    return d[pid]


def list_projects() -> list:
    return list(_load().values())


def get_project(pid: str):
    return _load().get(pid)


def get_active():
    """Most-recently-active non-closed project."""
    d = _load()
    candidates = [p for p in d.values() if p.get("status") != "closed"]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.get("last_active", ""))


def _resolve(pid: str | None) -> str | None:
    if pid and pid in _load():
        return pid
    a = get_active()
    return a["id"] if a else None


def update(pid: str | None = None, **fields) -> dict:
    d = _load()
    pid = _resolve(pid)
    if not pid:
        return {"error": "No active work project."}
    d[pid].update({k: v for k, v in fields.items() if v is not None})
    d[pid]["last_active"] = datetime.now().isoformat()
    _save(d)
    return d[pid]


def append_source(pid: str | None, source: dict) -> None:
    d = _load()
    pid = _resolve(pid)
    if not pid:
        return
    d[pid].setdefault("sources", []).append(source)
    d[pid]["last_active"] = datetime.now().isoformat()
    _save(d)


def append_gap(pid: str | None, gap: str) -> None:
    d = _load()
    pid = _resolve(pid)
    if not pid or not gap:
        return
    gaps = d[pid].setdefault("gaps", [])
    if gap not in gaps:
        gaps.append(gap)
    _save(d)


def append_idea(pid: str | None, idea: str) -> dict:
    d = _load()
    pid = _resolve(pid)
    if not pid:
        return {"error": "No active work project."}
    d[pid].setdefault("ideas", []).append({"date": date.today().isoformat(), "idea": idea})
    d[pid]["last_active"] = datetime.now().isoformat()
    _save(d)
    return d[pid]


def append_summary(pid: str | None, text: str) -> None:
    """Append a research summary block to the running summary."""
    d = _load()
    pid = _resolve(pid)
    if not pid or not text:
        return
    existing = d[pid].get("summary", "")
    stamp = date.today().isoformat()
    d[pid]["summary"] = (existing + f"\n\n[{stamp}] {text}").strip()[:6000]
    d[pid]["last_active"] = datetime.now().isoformat()
    _save(d)


def work_research(query: str, pid: str | None = None) -> dict:
    """Delegate a research task to Hermes (it spawns parallel subagents), append findings.

    Slow (subagent spawn + local model). Call this from a background thread for the UI.
    """
    from brain.tools import call_hermes
    rid = _resolve(pid)
    if not rid:
        return {"error": "No active work project. Start one first with work_start."}
    topic = get_project(rid)["topic"]
    prompt = (
        f"You are a research sub-agent for the project: '{topic}'.\n"
        f"Research this query thoroughly: {query}\n\n"
        f"Delegate to 2-3 parallel subagents to cover different angles, search the web, then "
        f"synthesize. Return EXACTLY three sections:\n"
        f"SUMMARY: a concise synthesis of what was found.\n"
        f"SOURCES: a short list of titles + URLs.\n"
        f"GAPS: the top 3 open questions / missing data / things to verify next.\n"
        f"Be concrete and brief."
    )
    result = call_hermes(prompt)
    append_summary(rid, f"Research on '{query}':\n{result}")

    # Light gap extraction: capture bullet lines in/after a GAPS section.
    in_gaps = False
    for line in result.splitlines():
        up = line.upper()
        if "GAP" in up and (":" in line or up.strip() == "GAPS"):
            in_gaps = True
            continue
        if in_gaps:
            l = line.strip(" -*\t•")
            if l and len(l) > 8:
                append_gap(rid, l[:200])
            elif not line.strip():
                in_gaps = False
    return {"ok": True, "project": rid, "result": result[:2000]}


def work_close(pid: str | None = None) -> dict:
    d = _load()
    pid = _resolve(pid)
    if not pid:
        return {"error": "No active work project."}
    d[pid]["status"] = "closed"
    d[pid]["last_active"] = datetime.now().isoformat()
    _save(d)
    return {"ok": True, "closed": pid}


def status_text(pid: str | None = None) -> str:
    """Compact human/LLM-readable status of a project."""
    p = get_project(_resolve(pid)) if _resolve(pid) else None
    if not p:
        return "No active work project. Say 'work on <topic>' to start one."
    lines = [f"WORK PROJECT: {p['topic']} (status: {p['status']})"]
    if p.get("goal"):
        lines.append(f"Goal: {p['goal']}")
    if p.get("next_action"):
        lines.append(f"Next action: {p['next_action']}")
    if p.get("summary"):
        lines.append(f"Summary so far:\n{p['summary'][:1200]}")
    if p.get("gaps"):
        lines.append("Open gaps:\n" + "\n".join(f"- {g}" for g in p["gaps"][:8]))
    if p.get("ideas"):
        lines.append("Recent ideas:\n" + "\n".join(f"- {i['idea']}" for i in p["ideas"][-5:]))
    if p.get("plan"):
        lines.append(f"Plan:\n{p['plan'][:800]}")
    lines.append(f"Sources gathered: {len(p.get('sources', []))}")
    return "\n".join(lines)


def active_context() -> str:
    """Short context block for injection into the system prompt (active project only)."""
    p = get_active()
    if not p:
        return ""
    parts = [f"Topic: {p['topic']}"]
    if p.get("next_action"):
        parts.append(f"Next action: {p['next_action']}")
    if p.get("summary"):
        parts.append(f"What we know:\n{p['summary'][:1500]}")
    if p.get("gaps"):
        parts.append("Open gaps:\n" + "\n".join(f"- {g}" for g in p["gaps"][:6]))
    if p.get("ideas"):
        parts.append("Ideas so far:\n" + "\n".join(f"- {i['idea']}" for i in p["ideas"][-4:]))
    if p.get("plan"):
        parts.append(f"Plan:\n{p['plan'][:600]}")
    return "\n".join(parts)
