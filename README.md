# Nexus — J.A.R.V.I.S.

A **local-first, sovereign personal AI** for Windows. Multi-tier brain on local models
(via Ollama), a proactive life-domain driver, a connector framework, a web dashboard,
and bridges to external local agents — all running on your machine. No cloud required.

> Built as the hackable, you-own-it alternative to centralized personal AI.

---

## What it can do (functions)

**Core brain**
- **Multi-tier routing** — classifies each message and routes to the right local model:
  Tier 1 `llama3.2:3b` (reflex/chat), Tier 2 `gemma3:4b` (tools/code), Tier 3 `hermes3:8b`
  (deep reasoning). Optional cloud Tier 3 (Claude) behind a daily budget cap, **off by default**.
- **Persistent memory** — Mem0 (local vector store + `nomic-embed-text`) remembers facts across
  sessions, auto-injected into context. Plus episodic logs and a simple JSON backup.
- **Modes** — `personal / office / content / freelance`; the active mode shapes responses.
- **JARVIS persona** — formal, analytical, decisions-over-options; addresses you as you choose.

**Life-domain driver** (the daily-driver core)
- Tracks your fronts (default: Research / Job Hunt / PhD / Content) as living state:
  **next action, deadline, staleness, overdue** — surfaced so you act, not deliberate.
- `domain_status` / `domain_update` tools; the dashboard shows live next-actions + overdue badges.
- **Proactive nudge**: a Signal Monitor flags overdue actions and notifies you.

**Daily briefing**
- Morning briefing that **leads with your domain priorities**, then weaves in fresh data
  (new papers, etc.). Evening reflection. Delivered via notification + the dashboard.

**Tools the agent can call**
- `web_search`, `run_command`, `get_time`, `read_file` / `write_file` / `list_dir` / `project_tree`,
  `run_python`, `recall` (RAG over your project files), `domain_status` / `domain_update`,
  `hermes_delegate` (hand a task to the Hermes agent), `council_verify` (multi-model bug-check).

**Connector framework** (50+ sources; many free/no-auth, some need keys)
- Free/no-auth: arXiv, HackerNews, RSS, USGS earthquakes, crypto, forex, F1, sunrise/sunset…
- Key/OAuth (optional): Google Calendar / Gmail / Tasks, Notion, weather, GitHub, and more.
- Each connector exposes MCP tools and can feed the briefing + ambient alerts.

**Interfaces**
- **Web dashboard** at `http://localhost:8765/` — domain cards, today's briefing line, chat box.
- **CLI** (`jarvis`) — chat REPL, slash-commands, and flags (see below).
- **Bridges** — `/hermes` (Hermes Agent), `/verify` (multi-model Council).
- Optional: desktop HUD overlay, voice (wake-word / push-to-talk / TTS), WhatsApp/Telegram gateways.

**Event automation** — clipboard / idle / file-created hooks can trigger agent actions.

---

## Requirements
- **Windows 10/11**, cloned to **`C:\jarvis`** (paths are currently hardcoded to this location).
- **Python 3.11+**, **Node.js** (for optional WhatsApp bridge), **Git**.
- **[Ollama](https://ollama.com/download)** installed.
- ~10 GB disk for the local models. A GPU helps but CPU works.

## Quick start
```powershell
git clone https://github.com/ParamBarodia/nexus C:\jarvis
cd C:\jarvis
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```
The installer creates a venv, installs deps, pulls the Ollama models, runs the **first-run
setup** (`jarvis --init` — your details go into gitignored `data\*.local.json`), adds `jarvis`
to PATH, and starts the brain. Then open **http://localhost:8765/**.

To start it later / on demand:
```powershell
powershell -File C:\jarvis\scripts\start_nexus.ps1     # starts Ollama + brain, opens dashboard
```
For auto-start at logon, the install/desktop shortcuts handle it (no admin needed).

## Using it
```powershell
jarvis                       # interactive chat
jarvis "what should I do next?"
jarvis --init                # (re)run profile setup
jarvis /hermes "task"        # delegate to the Hermes agent
jarvis /verify "a claim"     # multi-model council bug-check
jarvis --status              # health
jarvis --connectors          # list data connectors
jarvis --setup               # configure connector API keys
```

## Customize
- **Your profile & fronts**: `jarvis --init`, or edit `data\user.local.json`,
  `data\param_context.local.json`, `data\domains.local.json` (these override the shipped
  templates and are **gitignored** — your data never leaves your machine).
- **Connectors**: `jarvis --setup` or `POST /connectors/install`.
- **Cloud Tier 3** (optional): set `TIER3_CLOUD_ENABLED=true` + `ANTHROPIC_API_KEY` in `.env`.

## Privacy
100% local by default — models, memory, and your data stay on your machine. Personal data lives
only in gitignored `*.local.json` files. The repo ships **templates**, never anyone's real data.

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for the full map (brain, bridges, dashboard, data flow).

## Caveats (it's a personal project, shipped for testing)
- **Windows-only** and hardcoded to `C:\jarvis` (path portability is a known TODO).
- Some connectors are stubs; voice/HUD/WhatsApp are optional and need extra setup.
- The local models are small — great for routing, recall, and drafting; use `/verify` or cloud
  Tier 3 for high-stakes correctness.
