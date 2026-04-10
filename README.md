# NEXUS (J.A.R.V.I.S. v1.0)

Nexus is Param's sovereign personal AI — deliberately the opposite of Meta's centralized "Personal Superintelligence" and Anthropic's cloud Managed Agents. Local-first, hackable, India-aware, single-user. Built on best-in-class open-source plug-ins (Mem0, MCP, ChromaDB).

## Core Philosophy
- **Sovereignty**: Data stays at `C:\jarvis`. No cloud LLM by default.
- **Hackability**: Everything is Python/PowerShell. Custom India-specific MCP servers.
- **Contextual**: Mem0 + RAG ensure JARVIS knows everything about Param's projects.

## Multi-Tier Brain (Advisor Pattern)
- **Tier 1 (Reflex)**: `gemma2:2b` — Classification, chat, simple recall.
- **Tier 2 (Executor)**: `qwen2.5:7b` — Multi-step tools, code generation, file ops.
- **Tier 3 (Advisor)**: `qwen2.5:14b` (Local) or `Sonnet 3.5` (Cloud) — Planning, architecture.

## Quick Start (Nexus)

```powershell
# 1. Update Core
powershell -ExecutionPolicy Bypass -File C:\jarvis\scripts\install.ps1

# 2. Register a Project
jarvis --add-project "Satani Research" "C:\path\to\satani"

# 3. Use
jarvis "Sir, scan the research project and tell me the current focus."
```

## Advanced CLI
- `jarvis --status` — Check multi-tier health and active project.
- `jarvis --projects` — List registered scopes.
- `jarvis --use <id>` — Switch active project context.
- `jarvis --mode office|personal` — Switch domain system prompts.
- `jarvis --advisor "long message"` — Force Tier 3 reasoning.
- `jarvis --briefing` — Trigger proactive morning briefing.

## Architecture
- **Brain**: FastAPI + APScheduler + Watchdog.
- **Memory**: Mem0 + ChromaDB.
- **Tools**: MCP (Model Context Protocol).
- **Communication**: HTTP/SSE with Bearer Auth.
- **Remote Reach**: Cloudflare Tunnel (Opt-in).

---

## 24-Point Acceptance Checklist
1. Phase 0 Regressions (Gemma, Tools, Personality) - PASSED
2. Multi-tier Routing (logs/router.log) - PASSED
3. Mem0 High-fidelity Memory (logs/memory.log) - PASSED
4. Scoped File System (brain/fs.py) - PASSED
5. Knowledge RAG (brain/knowledge.py) - PASSED
6. India-Specific Tools (upi, irctc, etc.) - PASSED
7. Proactive Layer (ntfy.sh) - PASSED
8. System Integrity & Bearer Auth - PASSED
