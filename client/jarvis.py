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
            expand=False,
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


def do_backup():
    resp = requests.post(f"{BRAIN_URL}/backup", headers=get_headers(), timeout=60)
    console.print(f"[green]{resp.json().get('result', 'Done')}[/green]")


def do_export():
    resp = requests.post(f"{BRAIN_URL}/export", headers=get_headers(), timeout=60)
    console.print(f"[green]{resp.json().get('result', 'Done')}[/green]")


def list_backups():
    resp = requests.get(f"{BRAIN_URL}/backups", headers=get_headers())
    backups = resp.json()
    if not backups:
        console.print("[dim]No backups found.[/dim]")
        return
    table = Table(title="Backups")
    table.add_column("Name", style="cyan")
    table.add_column("Size MB", style="green")
    table.add_column("Created", style="dim")
    for b in backups:
        table.add_row(b["name"], str(b["size_mb"]), b["created"])
    console.print(table)


def do_restore(path):
    console.print(f"[yellow]This will restore from: {path}[/yellow]")
    confirm = input("Are you sure? (yes/no): ").strip().lower()
    if confirm in ("yes", "y"):
        resp = requests.post(f"{BRAIN_URL}/restore", json={"path": path}, headers=get_headers(), timeout=120)
        console.print(f"[green]{resp.json().get('result', 'Done')}[/green]")
    else:
        console.print("Restore cancelled.")


def list_skills():
    resp = requests.get(f"{BRAIN_URL}/skills", headers=get_headers())
    skills = resp.json()
    table = Table(title="Loaded Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Tier", style="green")
    table.add_column("Triggers", style="dim")
    for s in skills:
        table.add_row(s["name"], str(s["tier"]), ", ".join(s["triggers"][:3]))
    console.print(table)


def list_hooks_cmd():
    resp = requests.get(f"{BRAIN_URL}/hooks", headers=get_headers())
    hooks = resp.json()
    if not hooks:
        console.print("[dim]No hooks registered.[/dim]")
        return
    table = Table(title="Event Hooks")
    table.add_column("ID", style="dim")
    table.add_column("Trigger", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Enabled", style="yellow")
    for h in hooks:
        table.add_row(h["id"], h["trigger"], h["description"], str(h.get("enabled", True)))
    console.print(table)


def add_hook_cmd(description):
    # JARVIS interprets natural language hook description
    console.print(f"[dim]Creating hook from: {description}[/dim]")
    # Simple heuristic parsing — in practice JARVIS would LLM-parse this
    hook = {
        "trigger": "file_created",
        "description": description,
        "action": f"The user set up this hook: '{description}'. Execute the intent described.",
        "filters": {},
    }
    if "clipboard" in description.lower():
        hook["trigger"] = "clipboard_changed"
    elif "idle" in description.lower():
        hook["trigger"] = "user_idle"
    elif "pdf" in description.lower() or "download" in description.lower():
        hook["trigger"] = "file_created"
        hook["filters"] = {"extension": ".pdf"}

    resp = requests.post(f"{BRAIN_URL}/hooks/add", json=hook, headers=get_headers())
    if resp.json().get("ok"):
        console.print(f"[green]Hook created: {resp.json()['hook']['id']}[/green]")


def send_message(message: str, tier: int = None) -> None:
    try:
        resp = requests.post(
            f"{BRAIN_URL}/chat",
            json={"message": message, "tier": tier},
            stream=True,
            timeout=300,
            headers=get_headers(),
        )
        resp.raise_for_status()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    streaming = False
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            payload = line[6:]
        elif line.startswith("data:"):
            payload = line[5:]
        else:
            continue

        try:
            chunk = json.loads(payload)
        except Exception:
            continue

        chunk_type = chunk.get("type")
        if chunk_type == "routing":
            console.print(Text(f"  [routing: tier {chunk['tier']} - {chunk['reason']}]", style="dim italic"))
        elif chunk_type == "token":
            print(chunk.get("content", ""), end="", flush=True)
            streaming = True
        elif chunk_type == "text":
            console.print(Text(chunk.get("content", ""), style="cyan"))
        elif chunk_type == "tool_call":
            console.print(Text(f"\n  [tool: {chunk['tool']}({json.dumps(chunk['args'])})]", style="dim"))
        elif chunk_type == "tool_result":
            res = str(chunk.get("result", ""))
            preview = res[:100] + "..." if len(res) > 100 else res
            console.print(Text(f"  [result: {preview}]", style="dim"))
        elif chunk_type == "done":
            if streaming:
                print()
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

    # Backup flags
    parser.add_argument("--backup", action="store_true", help="Create backup now")
    parser.add_argument("--export", action="store_true", help="Export as markdown")
    parser.add_argument("--backups", action="store_true", help="List backups")
    parser.add_argument("--restore", metavar="PATH", help="Restore from backup")

    # Skills/Hooks
    parser.add_argument("--skills", action="store_true", help="List loaded skills")
    parser.add_argument("--hooks", action="store_true", help="List event hooks")
    parser.add_argument("--hook-add", metavar="DESC", help="Add hook from natural language")

    # Voice
    parser.add_argument("--listen", action="store_true", help="Ambient voice (wake word)")
    parser.add_argument("--push-to-talk", action="store_true", help="Push-to-talk voice")
    parser.add_argument("--voice-session", action="store_true", help="Full voice conversation")

    args = parser.parse_args()

    # Priority flags
    if args.status:
        check_status(); sys.exit(0)
    if args.projects:
        list_projects(); sys.exit(0)
    if args.add_project:
        add_project(args.add_project[0], args.add_project[1]); sys.exit(0)
    if args.use:
        switch_project(args.use); sys.exit(0)
    if args.mode:
        set_mode(args.mode); sys.exit(0)
    if args.briefing:
        trigger_briefing(); sys.exit(0)
    if args.backup:
        do_backup(); sys.exit(0)
    if args.export:
        do_export(); sys.exit(0)
    if args.backups:
        list_backups(); sys.exit(0)
    if args.restore:
        do_restore(args.restore); sys.exit(0)
    if args.skills:
        list_skills(); sys.exit(0)
    if args.hooks:
        list_hooks_cmd(); sys.exit(0)
    if args.hook_add:
        add_hook_cmd(args.hook_add); sys.exit(0)

    # Voice modes
    if args.listen:
        from brain.voice_session import run_ambient_listen
        run_ambient_listen()
        sys.exit(0)
    if args.push_to_talk:
        from brain.voice_session import run_push_to_talk
        run_push_to_talk()
        sys.exit(0)
    if args.voice_session:
        from brain.voice_session import run_voice_session
        run_voice_session()
        sys.exit(0)

    # REPL or single message
    tier = 3 if args.advisor else args.tier

    if args.message:
        send_message(" ".join(args.message), tier=tier)
    else:
        try:
            status = requests.get(f"{BRAIN_URL}/status", timeout=2, headers=get_headers()).json()
            p_ctx = f"[{status['mode']} | {status.get('project') or 'nexus'}]"
        except Exception:
            p_ctx = "[offline]"

        console.print(f"[bold cyan]J.A.R.V.I.S.[/bold cyan] — Nexus Core Online.")
        try:
            while True:
                user_input = input(f"{p_ctx} > ").strip()
                if not user_input:
                    continue
                send_message(user_input, tier=tier)
                console.print()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]Signing off, Sir.[/cyan]")


if __name__ == "__main__":
    main()
