# Nexus Super Intelligence Build — Implementation Plan

## Context
Nexus is a working multi-tier personal AI at C:\jarvis. This build transforms it from "personal AI with fixed tools" into a **universal connector framework** that can plug into any data source. Ships the framework, 20 real connectors (9 free/no-auth first), 30 real stub files, intelligent briefing composition, ambient awareness, 10 local capability tools, dashboard upgrade, bug fixes, and voice/experience polish. Additive only — nothing existing gets rewritten.

**User decisions:** No API keys ready (free connectors first), real stub files, 14B local for briefings, full ambient awareness.

---

## Execution Order (9 Phases)

```
Phase 0 (Bug Fixes)                          ← do first, unblocks confidence
    │
Phase 1 (Connector Framework Core)           ← foundation: base.py, auth.py, registry.py
    │
Phase 2 (9 Free Connectors, no API key)      ← validates framework end-to-end
    │
    ├── Phase 3 (11 API-Key Connectors)      ← credential prompts, built ready for when keys arrive
    ├── Phase 4 (Briefing + Ambient Layer)    ← uses connector data, 14B composition
    ├── Phase 5 (30 Real Stub Files)          ← parallelizable
    ├── Phase 6 (10 Capability Tools)         ← independent of connectors
    └── Phase 7 (Voice Polish + Dashboard)    ← independent
        │
Phase 8 (Memory Upgrades)                    ← last, needs everything else stable
```

---

## Phase 0 — Bug Fixes

### Fix 1: Brittle `_TOOL_KEYWORDS` in `brain/chat.py`
**Problem:** Hardcoded keyword list doesn't scale as connectors add tools.
**Fix:** Replace `_needs_tools()` to auto-derive from registered MCP tool names:
```python
def _needs_tools(message: str) -> bool:
    lower = message.lower()
    return any(name.replace("_", " ") in lower for name in mcp.tools.keys())
```
Delete the `_TOOL_KEYWORDS` list entirely.

### Fix 2: Unsafe asyncio in `brain/hooks.py:115-119`
**Problem:** `asyncio.get_running_loop()` fails from background threads (clipboard/idle watchers).
**Fix:** Use a dedicated thread with its own event loop:
```python
try:
    loop = asyncio.get_running_loop()
    loop.create_task(_run())
except RuntimeError:
    threading.Thread(target=lambda: asyncio.run(_run()), daemon=True).start()
```

### Fix 3: `TIER1_MODEL` hardcoded in `brain/models.py:19`
**Fix:** `TIER1_MODEL = os.getenv("TIER1_MODEL", "gemma2:2b")`
Add `TIER1_MODEL=gemma2:2b` to `.env`.

### Fix 4: Function-level imports in `brain/advisor_executor.py`
**Fix:** Move `import ollama`, `from brain.memory import append`, `from brain.memory_mem0 import add_memory` to module top-level. Keep `import anthropic` inside function (optional dep). Keep `from brain.models import get_model_for_tier` inside function (circular import avoidance).

### Fix 5: Dashboard hardcoded localhost in `dashboard/index.html:104`
**Fix:** `const API = window.location.origin;`
Add auth header helper for all fetch calls using token from localStorage (prompted on first load if empty).

### Fix 6: edge-tts in `brain/voice_session.py`
Addressed in Phase 7.

**Files modified:** `brain/chat.py`, `brain/hooks.py`, `brain/models.py`, `brain/advisor_executor.py`, `dashboard/index.html`, `.env`

---

## Phase 1 — Connector Framework Core

### New files

**`brain/connectors/__init__.py`** — empty package init

**`brain/connectors/base.py`** — abstract BaseConnector
```
class BaseConnector(ABC):
    name: str
    description: str
    category: str  # personal, environmental, news, markets, sports, dev
    poll_interval_minutes: int = 0  # 0 = on-demand only
    required_env: list[str] = []

    @abstractmethod
    async def fetch(self, params=None) -> dict
    @abstractmethod
    def briefing_summary(self) -> str
    async def health_check(self) -> dict
    def get_mcp_tools(self) -> list[dict]  # auto-registers MCP tools
```
Built-in caching (TTL), rate limiting, error isolation, logging.

**`brain/connectors/auth.py`** — encrypted credential manager
- Fernet key derived from `BRAIN_BEARER_TOKEN` via PBKDF2
- Salt stored at `data/.cred_salt`
- Credentials at `data/credentials.enc` (encrypted JSON blob)
- Functions: `store_credential(connector, key, value)`, `get_credential(connector, key)`, `has_credentials(connector)`, `delete_credentials(connector)`

**`brain/connectors/registry.py`** — connector marketplace
- `ConnectorRegistry` class
- `discover()` — scans `services/*.py` for BaseConnector subclasses
- `list_available()`, `list_active()`, `install(name, creds)`, `uninstall(name)`
- `get_all_mcp_tools()` — aggregates tools from all active connectors
- Active state tracked in `data/connectors_state.json`

**`brain/connectors/registry.yaml`** — metadata for all 50 connectors

**`brain/connectors/scheduler.py`** — per-connector polling
- `register_polling_jobs(registry, scheduler)` — adds APScheduler jobs for connectors with `poll_interval_minutes > 0`
- Publishes `Event("connector_data", {"connector": name, "data": result})` to EventBus

**`brain/connectors/services/__init__.py`** — empty

### Modified files

**`brain/mcp_client.py`** — add one method:
```python
def register_external_tools(self, tools: list[dict]):
    for t in tools:
        if t["name"] not in self.tools:
            self.tools[t["name"]] = t
```

**`brain/server.py`** — in startup_event(), after load_skills():
1. Discover connectors via ConnectorRegistry
2. Register MCP tools from active connectors
3. Register polling jobs on existing scheduler
4. Add endpoints: `GET /connectors`, `POST /connectors/install`, `POST /connectors/uninstall`, `GET /connectors/{name}/health`, `POST /connectors/{name}/fetch`

---

## Phase 2 — 9 Free Connectors (No API Key)

All in `brain/connectors/services/`. Each extends BaseConnector.

| # | Connector | API | MCP Tools | Poll |
|---|-----------|-----|-----------|------|
| 1 | `hackernews.py` | HN Algolia (free) | `hackernews_top`, `hackernews_search` | 60 min |
| 2 | `sunrise_sunset.py` | sunrise-sunset.org (free) | `sunrise_sunset` | 0 (on-demand) |
| 3 | `usgs_earthquakes.py` | earthquake.usgs.gov (free) | `earthquakes_recent` | 360 min |
| 4 | `arxiv_biorxiv.py` | arxiv.org API (free) | `arxiv_search`, `arxiv_recent` | 720 min |
| 5 | `f1_openf1.py` | api.openf1.org (free) | `f1_standings`, `f1_next_race` | 360 min |
| 6 | `crypto_coingecko.py` | coingecko.com (free) | `crypto_price`, `crypto_trending` | 30 min |
| 7 | `rss_aggregator.py` | feedparser (free) | `rss_latest`, `rss_add_feed` | 60 min |
| 8 | `reddit_watchlist.py` | reddit.com/.json (free) | `reddit_top` | 60 min |
| 9 | `currency_forex.py` | frankfurter.app (free) | `forex_rate`, `forex_convert` | 60 min |

Config files: `data/rss_feeds.json`, `data/reddit_watchlist.json` (user-editable)
User prefs in `.env`: `STOCK_WATCHLIST`, `CRYPTO_WATCHLIST`, `REDDIT_SUBS`, `HOME_LAT`, `HOME_LON`

---

## Phase 3 — 11 API-Key Connectors

Built with credential prompts — `jarvis --connector enable <name>` asks for key, encrypts, stores.

| # | Connector | Auth | Key Source |
|---|-----------|------|------------|
| 1 | `google_calendar.py` | OAuth2 | Google Cloud Console |
| 2 | `gmail_triage.py` | OAuth2 (shared) | Same Google OAuth |
| 3 | `google_tasks.py` | OAuth2 (shared) | Same Google OAuth |
| 4 | `notion.py` | Bearer token | notion.so/my-integrations |
| 5 | `openweathermap.py` | API key | openweathermap.org (free) |
| 6 | `waqi_airquality.py` | API key | aqicn.org (free) |
| 7 | `google_maps_traffic.py` | API key | Google Cloud ($200 free) |
| 8 | `newsapi.py` | API key | newsapi.org (free 100/day) |
| 9 | `indian_stocks_mf.py` | None (yfinance) | No key needed, uses yfinance |
| 10 | `cricket_cricapi.py` | API key | cricapi.com (free tier) |
| 11 | `github_notifications.py` | PAT | github.com/settings/tokens |

Note: `indian_stocks_mf` is technically free (uses yfinance), but grouped here because it needs the `yfinance` pip package.

Google OAuth flow: local callback server on `:9876`, token encrypted in `data/credentials.enc`, auto-refresh handled by google-auth library.

---

## Phase 4 — Intelligent Briefing + Ambient Awareness

### New files

**`brain/briefing/__init__.py`**

**`brain/briefing/context_engine.py`**
- `prefetch_all(registry)` — concurrent fetch from all active connectors via `asyncio.gather`
- `compose_briefing(prefetched, memories)` — sends connector summaries to qwen2.5:14b with JARVIS narrative prompt
- Saves to `data/briefings/YYYY-MM-DD.md`

**`brain/briefing/evening_synthesis.py`**
- `compose_reflection(registry)` — pulls today's conversations + connector events
- Sends to 14B: "What happened, what mattered, what's tomorrow"
- Saves to `data/reflections/YYYY-MM-DD.md`

**`brain/briefing/ambient_awareness.py`**
- `AmbientMonitor(registry)` class
- `check_all()` — runs every 15 min, checks: calendar (meeting in 15 min?), weather (severe alert?), stocks (threshold crossed?), GitHub (PR merged?)
- Fires `Event("ambient_alert", {...})` → Windows toast notification via Apprise

### Modified files

**`brain/proactive.py`** — replace hardcoded briefing text:
- Add 7:30 AM prefetch job
- `morning_briefing()` now reads from `data/briefings/` (composed by context_engine)
- `evening_reflection()` now uses evening_synthesis
- Add 15-min ambient check job

**`brain/server.py`** — add endpoints:
- `GET /briefing/today` — today's composed briefing
- `GET /briefing/reflection` — today's reflection
- `POST /briefing/compose` — manual trigger

---

## Phase 5 — 30 Real Stub Files

`brain/connectors/services/_stubs/` — each is a real Python file (~25 lines):
- Correct docstring with API URL, auth type, required env vars
- Real `BaseConnector` subclass
- `fetch()` raises `NotImplementedError("TODO: implement X API integration")`
- `health_check()` returns `{"healthy": False, "message": "Not implemented"}`

Stubs: spotify, youtube, todoist, trello, jira, slack, discord_bot, telegram_bot, twitch, steam, fitbit, strava, withings, home_assistant, openai_usage, aws_costs, azure_status, cloudflare, uptime_robot, pingdom, sentry, datadog, new_relic, docker_hub, npm_downloads, pypi_stats, producthunt, medium_stats, dev_to, linkedin_posts

Registry auto-discovers these with `status: stub` badge.

---

## Phase 6 — 10 Capability Tools

`brain/capabilities/` (NOT connectors — local system tools)

| Tool | Library | MCP Tool Name |
|------|---------|---------------|
| Screenshot + OCR | Pillow + pytesseract | `screenshot_ocr` |
| Active window | pygetwindow | `active_window` |
| Clipboard recall | pyperclip + ChromaDB | `clipboard_recall` |
| Browser history | sqlite3 (Chrome/Edge) | `browser_history` |
| Process monitor | psutil | `process_monitor` |
| System control | pycaw + screen-brightness-control | `volume_set`, `brightness_set` |
| Windows notify | plyer | `windows_notify` |
| File search | subprocess (where/dir) | `file_search` |
| PDF read | pdfplumber | `pdf_read` |
| Image describe | ollama (llava if available, else text-only) | `image_describe` |

Each exposes `get_tools() -> list[dict]` following MCP schema.
Registered in `server.py` startup via `register_all_capabilities(mcp)`.

---

## Phase 7 — Voice Polish + Dashboard Upgrade

### Voice
- Replace pyttsx3 with **edge-tts** (`en-GB-RyanNeural`) in `brain/voice_session.py`
- Fallback to pyttsx3 if offline
- Audio signatures: generate `listening.wav`, `thinking.wav`, `done.wav` via edge-tts at install time, store in `data/audio/`
- Play via `pygame.mixer` during voice sessions

### Dashboard (`dashboard/index.html`)
- **Connector marketplace grid** — all connectors with status badges (active/available/stub/error), install/disable buttons
- **Live connector data cards** — latest fetch from each active connector
- **Briefing preview** — today's composed narrative
- **Ambient events feed** — last 20 alerts with timestamps
- **WebSocket `/ws/live`** — real-time updates for connector data + ambient alerts, falls back to polling
- **Arc reactor pulse** — CSS animation on header, pulses cyan when brain active, deeper on Tier 3
- **Fix:** `window.location.origin` + auth headers (from Phase 0 fix)

### New server endpoints
- `WebSocket /ws/live` — broadcasts connector_data and ambient_alert events
- Existing endpoints stay, dashboard detects WS support and falls back gracefully

---

## Phase 8 — Memory Upgrades

**`brain/memory_enhanced.py`** — wraps existing `memory_mem0.py`

| Feature | How |
|---------|-----|
| Episodic memory | Daily conversation summaries in `data/episodes/YYYY-MM-DD.json` |
| Preference extraction | After each chat, extract "prefers X over Y" patterns, tag in Mem0 |
| Temporal decay | Weight memories by recency (30-day half-life) when retrieving |
| Contradiction detection | Before adding memory, search for conflicts, flag if found |

Integration: replace `add_memory` / `get_memories` calls in `chat.py` with enhanced wrappers. Existing Mem0 module stays untouched underneath.

---

## New Dependencies (`requirements.txt` additions)

```
# Connectors
feedparser
yfinance
google-auth-oauthlib
google-api-python-client
cryptography
httpx
# Capabilities
pytesseract
pygetwindow
psutil
pdfplumber
pycaw
plyer
screen-brightness-control
# Voice polish
edge-tts
pygame
```

## New `.env` additions

```
TIER1_MODEL=gemma2:2b
HOME_LAT=23.0225
HOME_LON=72.5714
REDDIT_SUBS=LocalLLaMA,neuroscience,india,IndianStreetBets
STOCK_WATCHLIST=RELIANCE.NS,INFY.NS,TCS.NS
CRYPTO_WATCHLIST=bitcoin,ethereum,solana
RSS_FEEDS=
TTS_BACKEND=edge
TTS_VOICE=en-GB-RyanNeural
```

---

## New CLI Commands

```
jarvis --connectors                    # list all with status
jarvis --connector enable <name>       # install + auth
jarvis --connector disable <name>      # uninstall
jarvis --connector test <name>         # health check + sample fetch
jarvis --briefing                      # manual morning briefing (enhanced)
jarvis --reflect                       # manual evening reflection
jarvis --screen                        # screenshot + OCR
jarvis --focus                         # active window info
```

---

## Verification Plan

### Framework verification (Phase 1)
```
curl http://localhost:8765/connectors  → returns list of discovered connectors
jarvis --connectors                    → shows 20 active + 30 stub in table
```

### Free connector verification (Phase 2)
```
jarvis top hacker news                 → real HN top 10
jarvis bitcoin price                   → real CoinGecko price
jarvis any new neuroscience papers     → real arxiv results
jarvis next f1 race                    → real OpenF1 schedule
jarvis usd to inr rate                 → real exchange rate
```

### Briefing verification (Phase 4)
```
jarvis --briefing → narrative from 14B weaving weather + news + markets naturally
# Expected output structure (not a list):
# "Good morning, Sir. Friday, April 10. Ahmedabad is 34°C, AQI moderate..."
```

### Dashboard verification (Phase 7)
```
Open http://localhost:8765/dashboard/
→ Connector marketplace grid visible with install buttons
→ Live data cards show latest connector fetches
→ Header pulses cyan
→ WebSocket connection established (check browser console)
```

### Capability tools verification (Phase 6)
```
jarvis --screen       → captures screen, returns OCR text
jarvis --focus        → returns active window name
jarvis what processes are using the most memory → psutil output
```

### Regression
All 28 previous acceptance tests must still pass (brain alive, tiers, tools, skills, hooks, backups, dashboard, personality).

---

## File Count Summary

| Category | New Files | Modified Files |
|----------|-----------|----------------|
| Framework core | 6 | 2 (mcp_client.py, server.py) |
| 9 Free connectors | 9 | 0 |
| 11 API connectors | 11 | 0 |
| 30 Stubs | 30 | 0 |
| Briefing layer | 4 | 1 (proactive.py) |
| 10 Capabilities | 11 | 1 (server.py) |
| Dashboard | 0 | 1 (index.html) |
| Voice polish | 0 | 1 (voice_session.py) |
| Memory | 1 | 1 (chat.py) |
| Bug fixes | 0 | 5 |
| Config | 2 (registry.yaml, connectors_state.json) | 2 (.env, requirements.txt) |
| **Total** | **~74 new** | **~10 modified** |
