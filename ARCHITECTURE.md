# Nexus / J.A.R.V.I.S. — Architecture

Param's local-first personal AI. Multi-tier brain + bridges to two external local systems
(Hermes Agent and the multi-model Council). Everything runs on local Ollama; no cloud
required except the optional free OpenRouter arbiter inside the Council.

## Layout
```
C:\jarvis\                      <- this repo
  brain\                        FastAPI brain (port 8765)
    server.py                   routes: /chat, /api/status, /api/chat, dashboard at /
    chat.py                     router -> tier -> tools -> memory
    models.py                   tier model registry (see Tiers below)
    prompt.py                   system prompt + injects data/param_context.json
    tools.py                    web_search, run_command, get_time, call_hermes, council_verify
    mcp_client.py               tool registry (incl. hermes_delegate, council_verify)
    briefing\, connectors\, capabilities\, ...
  client\jarvis.py              CLI: chat REPL + /hermes + /verify + flags
  dashboard\nexus.html          4-card dashboard (Research / Job Hunt / PhD / Content)
  data\
    user.json                   public profile (tracked)
    param_context.json          deep context Jarvis silently knows (tracked, force-added)
  scripts\register_autostart.ps1  registers NexusBrain (logon) + NexusSignalMonitor (+30min)
  .env                          model config (gitignored)
  venv\                         deps (gitignored)
```

## Tiers (local Ollama models)
| Tier | Model | Role |
|------|-------|------|
| 1 Reflex | `llama3.2:3b` | classification, fast chat |
| 2 Executor | `gemma3:4b` | tools, code, file ops |
| 3 Advisor | `hermes3:8b` (local) / `claude-sonnet-4-6` (cloud, opt-in) | planning |

## Bridges (external local systems)
- **Hermes Agent** — autonomous agent (40+ tools), at
  `C:\Users\Admin\AppData\Local\hermes`. Called via `call_hermes(task)` →
  `hermes -z "task"`. Exposed as MCP tool `hermes_delegate` and CLI `jarvis /hermes "..."`.
- **Council** — benchmark-ranked multi-model verifier at
  `C:\Users\Admin\ai-agents\council.py`. Called via `council_verify(content)` →
  `uv run council.py "content"`. Exposed as MCP tool `council_verify` and CLI `jarvis /verify "..."`.
  Local models draft + review; a free OpenRouter model (gpt-oss-120b) arbitrates.

## Run
```powershell
# brain server (or use scripts\register_autostart.ps1 from an ADMIN terminal)
C:\jarvis\venv\Scripts\python.exe -m uvicorn brain.server:app --host 127.0.0.1 --port 8765
# CLI
C:\jarvis\venv\Scripts\python.exe client\jarvis.py "status, Sir?"
C:\jarvis\venv\Scripts\python.exe client\jarvis.py /hermes "what time is it in Tokyo"
C:\jarvis\venv\Scripts\python.exe client\jarvis.py /verify "neurons learn"
# dashboard
start http://localhost:8765/
```

## Prerequisites
- **Ollama** running with `llama3.2:3b`, `gemma3:4b`, `hermes3:8b`
- venv built from `requirements.txt`
- Hermes Agent installed + wired to local Ollama
- Council at `ai-agents\` with its own `.env` (optional OpenRouter key)
