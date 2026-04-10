"""Message classification and tier routing logic."""

import json
import logging
from typing import TypedDict
import ollama
from brain.models import TIER1_MODEL

# Setup dedicated router log
LOG_FILE = r"C:\jarvis\logs\router.log"
router_logger = logging.getLogger("jarvis.router")
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
router_logger.addHandler(fh)
router_logger.setLevel(logging.INFO)

class RoutingDecision(TypedDict):
    tier: int
    confidence: float
    reason: str

ROUTER_PROMPT = """Classify the following user message into one of three tiers:
Tier 1: Reflex (chat, simple memory recall, single tool call like time, mode change)
Tier 2: Executor (multi-step tools, code generation, file operations, structured tasks)
Tier 3: Advisor (complex planning, hard reasoning, debugging, architecture, deep work)

Rules:
- Default to Tier 1 unless executor/advisor capabilities are clearly needed.
- If user message mentions "think harder", "use advisor", or "deep work", MUST use Tier 3.
- Output ONLY valid JSON: {{"tier": 1|2|3, "confidence": 0.0-1.0, "reason": "string"}}

User Message: {message}"""

def classify_message(message: str) -> RoutingDecision:
    """Uses the Tier 1 model to decide which tier should handle the message."""
    # Force tier 3 if keywords present
    lower_msg = message.lower()
    if any(kw in lower_msg for kw in ["think harder", "use advisor", "deep work"]):
        decision = {"tier": 3, "confidence": 1.0, "reason": "User explicitly requested advisor tier."}
        router_logger.info("Decision: %s | Message: %s", json.dumps(decision), message[:100])
        return decision

    try:
        response = ollama.chat(
            model=TIER1_MODEL,
            messages=[{"role": "user", "content": ROUTER_PROMPT.format(message=message)}],
            format="json",
            stream=False
        )
        content = response.get("message", {}).get("content", "{}")
        router_logger.info("Raw model output: %s", content)
        try:
            decision = json.loads(content)
        except:
            decision = {}

        if not isinstance(decision, dict) or "tier" not in decision:
            decision = {"tier": 1, "confidence": 0.5, "reason": "Model returned invalid or non-dictionary JSON."}
        
        # Validation
        if not isinstance(decision.get("tier"), int): decision["tier"] = 1
        if not isinstance(decision.get("confidence"), (int, float)): decision["confidence"] = 0.5
        if not isinstance(decision.get("reason"), str): decision["reason"] = "Defaulted due to validation error."
        
        router_logger.info("Decision: %s | Message: %s", json.dumps(decision), message[:100])
        return decision
    except Exception as e:
        router_logger.error("Routing error: %s", e)
        return {"tier": 1, "confidence": 0.0, "reason": f"Routing failed: {e}"}
