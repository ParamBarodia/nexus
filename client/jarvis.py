"""Nexus CLI client — advanced JARVIS terminal interface."""

import json
import os
import sys
import argparse
import requests
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

BRAIN_URL = os.environ.get("JARVIS_BRAIN_URL", "http://localhost:8765")
console = Console()

def get_headers():
    token = os.environ.get("BRAIN_BEARER_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}

def check_status() -> None:
    try:
        resp = requests.get(f"{BRAIN_URL}/status", timeout=5, headers=get_headers())
        data = resp.json()
        console.print(Panel(
            f"Mode: [bold green]{data.get('mode')}[/bold green]\n"
            f"Project: [bold cyan]{data.get('project', 'None')}[/bold cyan]\n"
            f"Memory: {data.get('memory_facts', 0)} facts",
            title="Nexus System Status",
            expand=False
        ))
    except Exception as e:
        console.print(f"[red]Could not reach Nexus brain: {e}[/red]")

def list_projects():
    resp = requests.get(f"{BRAIN_URL}/projects", headers=get_headers())
    projs = resp.json()
    table = Table(title="Registered Projects")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="green")
    for p in projs:
        table.add_row(p["id"], p["name"], p["path"])
    console.print(table)

def add_project(name, path):
    resp = requests.post(f"{BRAIN_URL}/projects/add", json={"name": name, "path": path}, headers=get_headers())
    if resp.json().get("ok"):
        console.print(f"[green]Project '{name}' registered, Sir.[/green]")
    else:
        console.print("[red]Failed to register project.[/red]")

def switch_project(project_id):
    resp = requests.post(f"{BRAIN_URL}/projects/use", json={"project_id": project_id}, headers=get_headers())
    if resp.json().get("ok"):
        console.print(f"[green]Switched to {project_id}, Sir.[/green]")

def set_mode(mode):
    resp = requests.post(f"{BRAIN_URL}/mode", json={"mode": mode}, headers=get_headers())
    if resp.json().get("ok"):
        console.print(f"[green]Mode updated to {mode}, Sir.[/green]")

def trigger_briefing():
    requests.post(f"{BRAIN_URL}/proactive/briefing", headers=get_headers())
    console.print("[green]Morning briefing triggered, Sir.[/green]")

def send_message(message: str, tier: int = None) -> None:
    try:
        resp = requests.post(
            f"{BRAIN_URL}/chat",
            json={"message": message, "tier": tier},
            stream=True,
            timeout=300,
            headers=get_headers()
        )
        resp.raise_for_status()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    streaming = False
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "): continue
        payload = line[6:]
        try:
            chunk = json.loads(payload)
        except: continue

        chunk_type = chunk.get("type")
        if chunk_type == "routing":
            console.print(Text(f"  [routing: tier {chunk['tier']} - {chunk['reason']}]", style="dim italic"))
        elif chunk_type == "token":
            print(chunk.get("content", ""), end="", flush=True)
            streaming = True
        elif chunk_type == "tool_call":
            console.print(Text(f"\n  [tool: {chunk['tool']}({json.dumps(chunk['args'])})]", style="dim"))
        elif chunk_type == "tool_result":
            res = str(chunk.get("result", ""))
            preview = res[:100] + "..." if len(res) > 100 else res
            console.print(Text(f"  [result: {preview}]", style="dim"))
        elif chunk_type == "done":
            if streaming: print()
            break

def main():
    parser = argparse.ArgumentParser(description="Nexus CLI")
    parser.add_argument("message", nargs="*", help="Message to send to JARVIS")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--projects", action="store_true")
    parser.add_argument("--add-project", nargs=2, metavar=("NAME", "PATH"))
    parser.add_argument("--use", metavar="PROJECT_ID")
    parser.add_argument("--mode", metavar="MODE_NAME")
    parser.add_argument("--briefing", action="store_true")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3])
    parser.add_argument("--advisor", action="store_true")
    
    args = parser.parse_args()

    # Priority flags
    if args.status: check_status(); sys.exit(0)
    if args.projects: list_projects(); sys.exit(0)
    if args.add_project: add_project(args.add_project[0], args.add_project[1]); sys.exit(0)
    if args.use: switch_project(args.use); sys.exit(0)
    if args.mode: set_mode(args.mode); sys.exit(0)
    if args.briefing: trigger_briefing(); sys.exit(0)

    # REPL or single message
    tier = 3 if args.advisor else args.tier
    
    if args.message:
        send_message(" ".join(args.message), tier=tier)
    else:
        # Get context for prompt
        try:
            status = requests.get(f"{BRAIN_URL}/status", timeout=2, headers=get_headers()).json()
            p_ctx = f"[{status['mode']} | {status['project'] or 'nexus'}]"
        except:
            p_ctx = "[offline]"

        console.print(f"[bold cyan]J.A.R.V.I.S.[/bold cyan] — Nexus Core Online.")
        try:
            while True:
                user_input = input(f"{p_ctx} > ").strip()
                if not user_input: continue
                send_message(user_input, tier=tier)
                console.print()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]Signing off, Sir.[/cyan]")

if __name__ == "__main__":
    main()
