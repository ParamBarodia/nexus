"""Nexus brain server: FastAPI logic for multi-tier operations."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from brain.chat import stream_chat
from brain.memory_mem0 import get_all_memories
import brain.projects as projects
import brain.modes as modes
import brain.proactive as proactive
import brain.knowledge as knowledge
from brain.models import TIER1_MODEL

# Load .env for token
from dotenv import load_dotenv
load_dotenv(r"C:\jarvis\.env")
BEARER_TOKEN = os.getenv("BRAIN_BEARER_TOKEN", "")

app = FastAPI(title="Nexus Brain", version="1.0.0")

# --- Startup ---
@app.on_event("startup")
async def startup_event():
    # Start scheduler
    proactive.start_scheduler()
    # Start watchers (non-blocking)
    import threading
    threading.Thread(target=knowledge.start_watchers, daemon=True).start()
    logging.info("Nexus systems initialized.")

# --- Auth Middleware ---
async def verify_token(authorization: Optional[str] = Header(None)):
    if BEARER_TOKEN and (not authorization or authorization != f"Bearer {BEARER_TOKEN}"):
        raise HTTPException(status_code=401, detail="Unauthorized")

# --- Endpoints ---

@app.get("/status")
async def status():
    active_proj = projects.get_active()
    return {
        "ok": True,
        "model": TIER1_MODEL,
        "mode": modes.get_current_mode(),
        "project": active_proj["name"] if active_proj else None,
        "memory_facts": len(get_all_memories())
    }

@app.post("/chat")
async def chat(request: dict):
    user_message = request.get("message", "")
    force_tier = request.get("tier")
    
    async def event_generator():
        async for chunk in stream_chat(user_message, force_tier=force_tier):
            yield {"data": json.dumps(chunk)}

    return EventSourceResponse(event_generator())

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

@app.post("/mode")
async def set_mode(req: dict):
    success = modes.set_mode(req["mode"])
    return {"ok": success}

@app.get("/memory/stats")
async def memory_stats():
    return {"count": len(get_all_memories())}

@app.post("/proactive/briefing")
async def trigger_briefing():
    await proactive.morning_briefing()
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    import os
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
