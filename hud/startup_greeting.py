"""Startup greeting — fetches top 3 updates from active connectors and speaks them."""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, r"C:\jarvis")

BRAIN_URL = "http://localhost:8765"
ENV_FILE = Path(r"C:\jarvis\.env")
BEARER_TOKEN = ""
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("BRAIN_BEARER_TOKEN="):
            BEARER_TOKEN = line.split("=", 1)[1].strip()


def _headers():
    return {"Authorization": f"Bearer {BEARER_TOKEN}"} if BEARER_TOKEN else {}


def _fetch(endpoint):
    try:
        return requests.get(f"{BRAIN_URL}{endpoint}", headers=_headers(), timeout=8).json()
    except Exception:
        return None


def _post(endpoint, data=None):
    try:
        return requests.post(f"{BRAIN_URL}{endpoint}", json=data or {}, headers=_headers(), timeout=15).json()
    except Exception:
        return None


def _wait_for_brain(max_wait=30):
    """Wait for the brain server to come online."""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = requests.get(f"{BRAIN_URL}/status", headers=_headers(), timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _speak(text):
    """Speak using edge-tts + Windows media playback."""
    try:
        import edge_tts
        import tempfile
        import subprocess

        voice = os.getenv("TTS_VOICE", "en-GB-RyanNeural")
        tmp_path = os.path.join(tempfile.gettempdir(), "nexus_greeting.mp3")

        asyncio.run(edge_tts.Communicate(text, voice).save(tmp_path))

        # Play using PowerShell media player (works on all Windows, no extra deps)
        ps_cmd = (
            f'Add-Type -AssemblyName PresentationCore; '
            f'$p = New-Object System.Windows.Media.MediaPlayer; '
            f'$p.Open([Uri]::new("{tmp_path}")); '
            f'$p.Play(); '
            f'Start-Sleep -Milliseconds 500; '
            f'while ($p.Position -lt $p.NaturalDuration.TimeSpan) {{ Start-Sleep -Milliseconds 200 }}; '
            f'$p.Close()'
        )
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            timeout=120, capture_output=True
        )

        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    except Exception as e:
        print(f"[TTS Error: {e}]")
        print(f"[JARVIS]: {text}")


def gather_updates():
    """Gather top 3 updates from active connectors."""
    updates = []

    # Weather
    weather = _post("/connectors/weather/fetch")
    if weather and "temp" in weather:
        desc = weather.get("description", "")
        temp = weather.get("temp", "")
        aqi = weather.get("aqi")
        aqi_label = weather.get("aqi_label", "")
        w_text = f"Weather is {desc}, {temp} degrees."
        if aqi:
            w_text += f" Air quality index is {aqi}, rated {aqi_label}."
        updates.append(w_text)

    # India News
    rss = _post("/connectors/rss/fetch")
    if rss and "articles" in rss and rss["articles"]:
        top_article = rss["articles"][0]
        updates.append(f"Top headline: {top_article['title']}.")

    # Crypto
    crypto = _post("/connectors/crypto/fetch")
    if crypto and "prices" in crypto:
        btc = crypto["prices"].get("bitcoin", {})
        if btc:
            price = btc.get("usd", 0)
            change = btc.get("change_24h", 0)
            direction = "up" if change >= 0 else "down"
            updates.append(f"Bitcoin is at ${price:,.0f}, {direction} {abs(change):.1f}% in 24 hours.")

    # Hacker News
    hn = _post("/connectors/hackernews/fetch")
    if hn and "stories" in hn:
        top = hn["stories"][0] if hn["stories"] else None
        if top:
            updates.append(f"Top on Hacker News: {top['title']}, with {top['points']} points.")

    # Earthquakes
    quakes = _post("/connectors/usgs_earthquakes/fetch")
    if quakes and "earthquakes" in quakes and quakes["earthquakes"]:
        q = quakes["earthquakes"][0]
        updates.append(f"Seismic activity: magnitude {q['magnitude']} earthquake near {q['place']}.")

    # Forex fallback
    if len(updates) < 3:
        forex = _post("/connectors/forex/fetch")
        if forex and "rates" in forex:
            inr = forex["rates"].get("INR")
            if inr:
                updates.append(f"Dollar to Rupee is at {inr}.")

    return updates[:3]


def gather_setup_needed():
    """Check which connectors need setup and return prompts."""
    connectors = _fetch("/connectors")
    if not connectors:
        return []

    setup_items = []
    for c in connectors:
        if c["status"] == "available" and c.get("required_env"):
            setup_items.append({
                "name": c["name"],
                "description": c["description"],
                "needs": c["required_env"],
            })
    return setup_items


def run_greeting():
    """Main startup greeting flow."""
    print("[Nexus] Waiting for brain server...")
    if not _wait_for_brain(30):
        print("[Nexus] Brain server not reachable. Skipping greeting.")
        return

    now = datetime.now()
    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    day_str = now.strftime("%A, %B %d")

    # Gather live updates
    updates = gather_updates()
    setup = gather_setup_needed()

    # Build the speech
    speech_parts = [f"{greeting}, Sir. {day_str}. Systems are online."]

    if updates:
        speech_parts.append("Here are your top updates.")
        for i, u in enumerate(updates, 1):
            speech_parts.append(u)

    if setup:
        count = len(setup)
        names = ", ".join(s["name"] for s in setup[:5])
        speech_parts.append(
            f"Sir, {count} connectors are available but need API keys to activate. "
            f"Including {names}. Shall I walk you through the setup?"
        )

    full_speech = " ".join(speech_parts)
    print(f"\n[JARVIS]: {full_speech}\n")
    _speak(full_speech)

    # Wait for user response, then deliver briefing
    print("[Nexus] Waiting for your response before briefing...")
    try:
        user_input = input("[You]: ").strip()
    except (EOFError, KeyboardInterrupt):
        user_input = ""

    if user_input:
        print(f"[Nexus] Acknowledged: {user_input}")

    # Compose and deliver briefing
    print("[Nexus] Composing briefing...")
    _post("/briefing/compose")
    briefing = _fetch("/briefing/today")
    briefing_text = briefing.get("briefing", "") if briefing else ""

    if briefing_text:
        # Truncate for voice (keep under 90 seconds of speech ~ 800 chars)
        voice_briefing = briefing_text[:800]
        if len(briefing_text) > 800:
            voice_briefing += "... The full briefing is on your HUD, Sir."

        print(f"\n[JARVIS BRIEFING]:\n{briefing_text[:1000]}\n")
        _speak(voice_briefing)
    else:
        fallback = "I wasn't able to compose a full briefing at this time, Sir. The live data is on your HUD."
        print(f"\n[JARVIS]: {fallback}\n")
        _speak(fallback)


if __name__ == "__main__":
    run_greeting()
