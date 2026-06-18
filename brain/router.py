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
Tier 1: Reflex (short chat, simple personal recall about the user, single tool like time/mode)
Tier 2: Executor (multi-step tools, code generation, file operations, structured tasks)
Tier 3: Smart/Advisor (complex reasoning, planning, debugging, architecture; general-knowledge or
        world questions; explanations; "why/how" reasoning; anything needing current/web info;
        conversational depth)

Rules:
- Default to Tier 1 for short chat or personal recall like "what is my X".
- If the message mentions reading, writing, or listing files, MUST use Tier 2.
- General-knowledge/world questions, explanations, "why/how" reasoning, or anything needing
  current or web information -> Tier 3.
- If the message mentions "think harder", "use advisor", or "deep work", MUST use Tier 3.
- Output ONLY valid JSON: {{"tier": 1|2|3, "confidence": 0.0-1.0, "reason": "string"}}

User Message: {message}"""

# Fast-path keywords that signal a hard/conversational/general-knowledge query -> smart tier.
SMART_KEYWORDS = [
    "think harder", "use advisor", "deep work", "explain", "how does", "how do i",
    "compare", "analyze", "analyse", "strategy", "architect", "design a", "deep dive",
    "in depth", "pros and cons", "why is", "why does", "latest", "search the web",
    "what's new", "current state", "research ",
]


def classify_message(message: str) -> RoutingDecision:
    """Uses the Tier 1 model to decide which tier should handle the message."""
    lower_msg = message.lower()
    # Personal recall ("what is my ...") stays local/fast — don't send to the smart tier.
    is_personal = lower_msg.startswith(("what is my", "what's my", "what are my", "who is my"))
    if not is_personal and any(kw in lower_msg for kw in SMART_KEYWORDS):
        decision = {"tier": 3, "confidence": 0.9, "reason": "Complex/conversational query -> smart tier."}
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
        try:
            decision["tier"] = int(decision.get("tier", 1))
        except (ValueError, TypeError):
            decision["tier"] = 1
            
        if not isinstance(decision.get("confidence"), (int, float)): decision["confidence"] = 0.5
        if not isinstance(decision.get("reason"), str): decision["reason"] = "Defaulted due to validation error."
        
        router_logger.info("Decision: %s | Message: %s", json.dumps(decision), message[:100])
        return decision
    except Exception as e:
        router_logger.error("Routing error: %s", e)
        return {"tier": 1, "confidence": 0.0, "reason": f"Routing failed: {e}"}
