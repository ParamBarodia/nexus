"""FastAPI server for the Jarvis brain."""

import json
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from brain.chat import stream_chat, MODEL
from brain.memory import clear, load_memory

# --- Logging setup ---
LOG_DIR = Path(r"C:\jarvis\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "jarvis.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("jarvis.server")

app = FastAPI(title="Jarvis Brain", version="0.1.0")


@app.get("/status")
async def status() -> JSONResponse:
    """Return brain health and model info."""
    memory = load_memory()
    return JSONResponse({
        "ok": True,
        "model": MODEL,
        "memory_turns": len(memory),
    })


@app.post("/reset")
async def reset() -> JSONResponse:
    """Clear conversation memory."""
    clear()
    logger.info("Memory reset via API")
    return JSONResponse({"ok": True})


@app.post("/chat")
async def chat(request: dict) -> EventSourceResponse:
    """Stream a chat response as SSE events."""
    user_message = request.get("message", "")
    logger.info("User: %s", user_message[:500])

    async def event_generator():
        async for chunk in stream_chat(user_message):
            logger.info("Chunk: %s", json.dumps(chunk)[:500])
            yield {"data": json.dumps(chunk)}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
