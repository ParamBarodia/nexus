"""Nexus brain server: FastAPI logic for multi-tier operations."""

import json
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from typing import Optional

from brain.chat import stream_chat
from brain.memory_mem0 import get_all_memories
import brain.projects as projects
import brain.modes as modes
import brain.proactive as proactive
import brain.knowledge as knowledge
import brain.backup as backup
from brain.skills_loader import load_skills, get_skills
from brain.hooks import register_event_listeners, list_hooks, add_hook, toggle_hook, remove_hook
from brain.events import ClipboardEventSource, IdleEventSource
from brain.models import TIER1_MODEL

from dotenv import load_dotenv
load_dotenv(r"C:\jarvis\.env")
BEARER_TOKEN = os.getenv("BRAIN_BEARER_TOKEN", "")
WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"

app = FastAPI(title="Nexus Brain", version="2.0.0")

# Serve dashboard
DASHBOARD_DIR = Path(r"C:\jarvis\dashboard")
if DASHBOARD_DIR.exists():
    app.mount("/dashboard", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")

# --- Startup ---
@app.on_event("startup")
async def startup_event():
    # Load skills
    load_skills()
    # Start scheduler (briefings + backups)
    proactive.start_scheduler()
    # Register event hook listeners
    register_event_listeners()
    # Start clipboard/idle watchers
    clipboard_src = ClipboardEventSource(min_length=100)
    clipboard_src.start()
    idle_src = IdleEventSource(idle_minutes=30)
    idle_src.start()
    # Start file watchers (non-blocking)
    import threading
    threading.Thread(target=knowledge.start_watchers, daemon=True).start()
    logging.info("Nexus systems initialized.")

# --- Auth ---
async def verify_token(authorization: Optional[str] = Header(None)):
    if BEARER_TOKEN and (not authorization or authorization != f"Bearer {BEARER_TOKEN}"):
        raise HTTPException(status_code=401, detail="Unauthorized")

# --- Core ---

@app.get("/status")
async def status():
    active_proj = projects.get_active()
    return {
        "ok": True,
        "model": TIER1_MODEL,
        "mode": modes.get_current_mode(),
        "project": active_proj["name"] if active_proj else None,
        "memory_facts": len(get_all_memories()),
    }

@app.post("/chat")
async def chat(request: dict):
    user_message = request.get("message", "")
    force_tier = request.get("tier")

    async def event_generator():
        async for chunk in stream_chat(user_message, force_tier=force_tier):
            yield {"data": json.dumps(chunk)}

    return EventSourceResponse(event_generator())

# --- Projects ---

@app.get("/projects")
async def list_projs():
    return projects.list_projects()

@app.post("/projects/add")
async def add_proj(req: dict):
    success = projects.add_project(req["name"], req["path"], req.get("description", ""))
    return {"ok": success}

@app.post("/projects/use")
async def use_proj(req: dict):
    success = projects.set_active(req["project_id"])
    return {"ok": success}

@app.get("/projects/scan/{project_id}")
async def scan_proj(project_id: str):
    return projects.scan_project(project_id)

# --- Mode ---

@app.post("/mode")
async def set_mode(req: dict):
    success = modes.set_mode(req["mode"])
    return {"ok": success}

# --- Memory ---

@app.get("/memory/stats")
async def memory_stats():
    return {"count": len(get_all_memories())}

# --- Proactive ---

@app.post("/proactive/briefing")
async def trigger_briefing():
    await proactive.morning_briefing()
    return {"ok": True}

# --- Backup ---

@app.post("/backup")
async def do_backup():
    result = backup.backup_all()
    return {"ok": True, "result": result}

@app.post("/export")
async def do_export():
    result = backup.export_human_readable()
    return {"ok": True, "result": result}

@app.get("/backups")
async def get_backups():
    return backup.list_backups()

@app.post("/restore")
async def do_restore(req: dict):
    result = backup.restore_from_backup(req["path"])
    return {"ok": True, "result": result}

# --- Skills ---

@app.get("/skills")
async def get_skills_list():
    return [{"name": s["name"], "description": s["description"],
             "triggers": s["triggers"], "tier": s["tier"]} for s in get_skills()]

# --- Hooks ---

@app.get("/hooks")
async def get_hooks():
    return list_hooks()

@app.post("/hooks/add")
async def create_hook(req: dict):
    hook = add_hook(
        trigger=req["trigger"],
        description=req["description"],
        action=req["action"],
        filters=req.get("filters"),
        enabled=req.get("enabled", True),
    )
    return {"ok": True, "hook": hook}

@app.post("/hooks/toggle")
async def toggle_hook_endpoint(req: dict):
    result = toggle_hook(req["hook_id"])
    return {"ok": result is not None, "enabled": result}

@app.post("/hooks/remove")
async def remove_hook_endpoint(req: dict):
    return {"ok": remove_hook(req["hook_id"])}

# --- Costs ---

@app.get("/costs")
async def get_costs():
    from brain.advisor_executor import _get_today_spend, DAILY_LIMIT_USD, COSTS_LOG
    today_spend = _get_today_spend()
    history = []
    if COSTS_LOG.exists():
        for line in COSTS_LOG.read_text(encoding="utf-8").splitlines()[-50:]:
            try:
                history.append(json.loads(line))
            except Exception:
                pass
    return {
        "today_usd": round(today_spend, 4),
        "daily_limit_usd": DAILY_LIMIT_USD,
        "recent": history,
    }

# --- WhatsApp ---

@app.get("/whatsapp/status")
async def wa_status():
    if not WHATSAPP_ENABLED:
        return {"enabled": False, "connected": False}
    from brain.whatsapp.client import get_status, get_qr
    status = get_status()
    status["enabled"] = True
    if not status.get("connected"):
        status["qr"] = get_qr()
    return status

@app.post("/whatsapp/incoming")
async def wa_incoming(req: dict):
    """Receive incoming WhatsApp message from Node bridge, process, and return reply."""
    from_number = req.get("from", "")
    body = req.get("body", "")

    if not body:
        return {"reply": None}

    # Process through chat engine
    response_parts = []
    async for chunk in stream_chat(body, force_tier=None):
        if chunk["type"] == "token":
            response_parts.append(chunk["content"])
        elif chunk["type"] == "text":
            response_parts.append(chunk["content"])

    reply = "".join(response_parts)
    logging.info("WhatsApp: %s -> %s", from_number, reply[:100])
    return {"reply": reply}

# --- Dashboard Actions ---

@app.post("/api/action")
async def dashboard_action(req: dict):
    action = req.get("action")
    if action == "backup_now":
        result = backup.backup_all()
        return {"ok": True, "result": result}
    elif action == "toggle_hook":
        result = toggle_hook(req.get("hook_id", ""))
        return {"ok": result is not None, "enabled": result}
    return {"ok": False, "error": "Unknown action"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
