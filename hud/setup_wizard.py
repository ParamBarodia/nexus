"""Setup wizard — shows which connectors need API keys and helps configure them."""

import sys
import os
sys.path.insert(0, r"C:\jarvis")

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path

BRAIN_URL = "http://localhost:8765"
ENV_FILE = Path(r"C:\jarvis\.env")
BEARER_TOKEN = ""
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("BRAIN_BEARER_TOKEN="):
            BEARER_TOKEN = line.split("=", 1)[1].strip()

console = Console()


def _headers():
    return {"Authorization": f"Bearer {BEARER_TOKEN}"} if BEARER_TOKEN else {}


SETUP_GUIDES = {
    "openweathermap": {
        "url": "https://openweathermap.org/appid",
        "env_key": "OPENWEATHERMAP_API_KEY",
        "instructions": "Sign up free, get API key from your account page.",
        "free_tier": "60 calls/min, current weather + 5-day forecast",
    },
    "newsapi": {
        "url": "https://newsapi.org/register",
        "env_key": "NEWSAPI_KEY",
        "instructions": "Register free, copy API key from dashboard.",
        "free_tier": "100 requests/day, headlines + search",
    },
    "waqi_airquality": {
        "url": "https://aqicn.org/data-platform/token/",
        "env_key": "WAQI_API_KEY",
        "instructions": "Request free token via the link.",
        "free_tier": "Unlimited for personal use",
    },
    "cricket_cricapi": {
        "url": "https://cricapi.com/",
        "env_key": "CRICAPI_KEY",
        "instructions": "Sign up, free plan gives 100 requests/day.",
        "free_tier": "100 requests/day, live scores + schedule",
    },
    "github_notifications": {
        "url": "https://github.com/settings/tokens",
        "env_key": "GITHUB_PAT",
        "instructions": "Create a Personal Access Token with 'notifications' and 'repo' scopes.",
        "free_tier": "5000 requests/hour",
    },
    "google_calendar": {
        "url": "https://console.cloud.google.com/apis/credentials",
        "env_key": "GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET",
        "instructions": "Create OAuth2 credentials in Google Cloud Console. Enable Calendar, Gmail, Tasks APIs.",
        "free_tier": "Full access with OAuth2",
    },
    "notion": {
        "url": "https://www.notion.so/my-integrations",
        "env_key": "NOTION_TOKEN",
        "instructions": "Create an integration, copy the Internal Integration Token.",
        "free_tier": "Full access to shared pages",
    },
    "google_maps_traffic": {
        "url": "https://console.cloud.google.com/apis/credentials",
        "env_key": "GOOGLE_MAPS_API_KEY",
        "instructions": "Enable Directions API, create API key. $200/month free credit.",
        "free_tier": "$200 free monthly credit",
    },
}


def run_wizard():
    """Interactive setup wizard."""
    console.print(Panel(
        "[bold cyan]N E X U S[/bold cyan] — Connector Setup Wizard\n"
        "[dim]Configure API keys to unlock more intelligence sources.[/dim]",
        expand=False
    ))

    # Fetch connector list
    try:
        r = requests.get(f"{BRAIN_URL}/connectors", headers=_headers(), timeout=5)
        connectors = r.json()
    except Exception as e:
        console.print(f"[red]Cannot reach brain server: {e}[/red]")
        return

    # Categorize
    active = [c for c in connectors if c["status"] == "active"]
    available = [c for c in connectors if c["status"] == "available"]
    stubs = [c for c in connectors if c["status"] == "stub"]

    # Status summary
    console.print(f"\n[green]{len(active)} active[/green] | "
                  f"[cyan]{len(available)} ready to enable[/cyan] | "
                  f"[yellow]{len(stubs)} stubs (not yet built)[/yellow]\n")

    # Active connectors
    if active:
        console.print("[bold green]Active connectors:[/bold green]")
        for c in active:
            console.print(f"  [green]{c['name']}[/green] — {c['description']}")
        console.print()

    # Available connectors that need setup
    if available:
        table = Table(title="Available — Need API Keys", show_lines=False)
        table.add_column("Connector", style="cyan")
        table.add_column("Description", style="dim")
        table.add_column("Setup", style="yellow")
        table.add_column("Free Tier", style="green")

        for c in available:
            guide = SETUP_GUIDES.get(c["name"], {})
            setup_url = guide.get("url", "Check connector docs")
            free_tier = guide.get("free_tier", "Check provider")
            table.add_row(c["name"], c["description"][:50], setup_url, free_tier)

        console.print(table)
        console.print()

        # Interactive: ask user which to set up
        console.print("[bold]Would you like to configure any? Enter connector name (or 'skip'):[/bold]")
        while True:
            choice = input("> ").strip().lower()
            if choice in ("skip", "quit", "exit", "q", ""):
                break

            guide = SETUP_GUIDES.get(choice)
            if not guide:
                console.print(f"[dim]No setup guide for '{choice}'. Try another or 'skip'.[/dim]")
                continue

            console.print(f"\n[bold cyan]{choice}[/bold cyan]")
            console.print(f"  URL: [link={guide['url']}]{guide['url']}[/link]")
            console.print(f"  Instructions: {guide['instructions']}")
            console.print(f"  Free tier: [green]{guide['free_tier']}[/green]")
            console.print(f"  Env key: [yellow]{guide['env_key']}[/yellow]\n")

            api_key = input(f"  Paste your API key for {choice} (or Enter to skip): ").strip()
            if api_key:
                # Store via brain API
                try:
                    r = requests.post(
                        f"{BRAIN_URL}/connectors/install",
                        json={"name": choice, "credentials": {"api_key": api_key}},
                        headers=_headers(), timeout=10
                    )
                    result = r.json()
                    if result.get("ok"):
                        console.print(f"  [green]{choice} enabled and credentials stored![/green]\n")
                    else:
                        console.print(f"  [red]Failed: {result.get('error', 'Unknown')}[/red]\n")
                except Exception as e:
                    console.print(f"  [red]Error: {e}[/red]\n")

            console.print("[bold]Another connector? (name or 'skip'):[/bold]")

    # Stubs info
    if stubs:
        console.print(f"\n[yellow]{len(stubs)} stub connectors[/yellow] [dim](placeholders — not yet implemented):[/dim]")
        names = ", ".join(s["name"] for s in stubs)
        console.print(f"  [dim]{names}[/dim]")
        console.print(f"  [dim]These are planned integrations. They'll be built in future updates.[/dim]\n")

    console.print("[cyan]Setup complete, Sir. Nexus is ready.[/cyan]")


if __name__ == "__main__":
    run_wizard()
