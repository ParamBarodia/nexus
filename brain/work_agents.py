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


def _synthesize(prompt: str) -> str:
    """Synthesize text using the FREE smart tier (OpenRouter), falling back to local.

    Runs synchronously — only ever called from a background research thread, never on
    the event loop. Prefers free cloud (no GPU cost, better quality) and falls back to
    the local Tier-3 model directly (no flaky Hermes subprocess).
    """
    from brain.models import (OPENROUTER_API_KEY, OPENROUTER_MODEL,
                              TIER3_OPENROUTER_ENABLED, TIER3_LOCAL_MODEL)

    # 1) Free OpenRouter smart tier (zero GPU, frontier-ish quality).
    if TIER3_OPENROUTER_ENABLED and OPENROUTER_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENROUTER_API_KEY,
                            base_url="https://openrouter.ai/api/v1",
                            max_retries=0, timeout=60)
            for model in [OPENROUTER_MODEL, "openai/gpt-oss-120b:free"]:
                try:
                    r = client.chat.completions.create(
                        model=model, messages=[{"role": "user", "content": prompt}])
                    txt = (r.choices[0].message.content or "").strip()
                    if txt:
                        return txt
                except Exception as e:
                    logger.warning("Synthesis model %s unavailable: %s", model, e)
                    continue
        except Exception as e:
            logger.warning("OpenRouter synthesis unavailable: %s", e)

    # 2) Local fallback — direct Ollama (no Hermes subprocess).
    try:
        import ollama
        r = ollama.chat(model=TIER3_LOCAL_MODEL,
                        messages=[{"role": "user", "content": prompt}])
        return (r.get("message", {}).get("content", "") or "").strip()
    except Exception as e:
        logger.error("Local synthesis failed: %s", e)
        return f"(synthesis unavailable: {e})"


def work_research(query: str, pid: str | None = None) -> dict:
    """Research a query: gather real web evidence, then synthesize with the smart tier.

    Pipeline = free web search (DDG/Tavily) -> free smart-tier synthesis. Costs $0 and no
    GPU. Slow-ish (network); call from a background thread for the UI. (Hermes remains
    available via its own tool/CLI for tasks needing its 40+ autonomous tools.)
    """
    from brain.mcp_client import mcp
    rid = _resolve(pid)
    if not rid:
        return {"error": "No active work project. Start one first with work_start."}
    topic = get_project(rid)["topic"]

    # 1) Gather real web evidence across a few angles (free backend).
    angles = [query,
              f"{topic} state of the art recent advances",
              f"{topic} open problems limitations challenges"]
    snippets, source_lines = [], []
    for q in angles:
        try:
            res = str(mcp.call_tool("web_search", {"query": q}))
            if res and "Error" not in res[:20]:
                snippets.append(f"### Results for: {q}\n{res[:2000]}")
                source_lines.append(res)
        except Exception as e:
            logger.warning("web_search failed for %r: %s", q, e)
    evidence = "\n\n".join(snippets) or "(no web results retrieved)"

    # 2) Synthesize concrete SUMMARY / SOURCES / GAPS from the evidence.
    prompt = (
        f"You are a sharp research analyst for the project: '{topic}'.\n"
        f"Using the web search results below, answer this query: {query}\n\n"
        f"{evidence}\n\n"
        f"Return EXACTLY three sections, concrete and brief (no preamble):\n"
        f"SUMMARY: 4-8 sentences on the current state and what is practically possible.\n"
        f"SOURCES: bullet list of the most relevant titles + URLs from the results.\n"
        f"GAPS: the top 3-5 open questions / missing data / things to verify next."
    )
    result = _synthesize(prompt)
    append_summary(rid, f"Research on '{query}':\n{result}")

    # Light gap extraction: capture bullet lines under a GAPS section. Section headers
    # may be markdown-styled ("**GAPS**", "## GAPS:", "GAPS:"), so normalise first.
    in_gaps = False
    for line in result.splitlines():
        norm = line.strip().strip("*#").strip().rstrip(":").upper()
        if norm.startswith("GAP"):
            in_gaps = True
            continue
        if in_gaps:
            if norm.startswith("SUMMARY") or norm.startswith("SOURCE"):
                in_gaps = False  # left the GAPS section
                continue
            l = line.strip(" -*\t•#0123456789.")
            if l and len(l) > 8:
                append_gap(rid, l[:200])

    # Record any URLs the synthesis cited as sources.
    import re
    for url in re.findall(r"https?://[^\s)\]]+", result):
        append_source(rid, {"url": url[:300], "date": date.today().isoformat()})

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
