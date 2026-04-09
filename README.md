# J.A.R.V.I.S. — Phase 0

Personal AI assistant for Param Barodia. Runs Gemma 4 E4B locally via Ollama.

## Quick Start

```powershell
# Install (run once)
powershell -ExecutionPolicy Bypass -File C:\jarvis\scripts\install.ps1

# Use (from any terminal)
jarvis

# Commands
jarvis --status    # Check brain health
jarvis --reset     # Clear conversation memory
```

## Architecture

- **Brain** — FastAPI server on `localhost:8765`, interfaces with Gemma 4 via Ollama
- **CLI Client** — Rich-powered terminal interface, connects to brain via HTTP/SSE

## Files

- `brain/` — Server, chat engine, memory, tools, prompt
- `client/` — CLI entry point
- `data/` — User profile and conversation memory
- `logs/` — Brain logs
- `scripts/` — Install, start, stop scripts

## Tools

1. `web_search` — DuckDuckGo Instant Answer API
2. `run_command` — Execute Windows shell commands
3. `get_time` — Current date and time

## Manual Brain Control

```powershell
# Start
powershell -ExecutionPolicy Bypass -File C:\jarvis\scripts\start_brain.ps1

# Stop
powershell -ExecutionPolicy Bypass -File C:\jarvis\scripts\stop_brain.ps1
```
