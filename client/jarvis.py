"""Jarvis CLI client — talk to the brain from any terminal."""

import json
import os
import sys

import requests
from rich.console import Console
from rich.text import Text

BRAIN_URL = os.environ.get("JARVIS_BRAIN_URL", "http://localhost:8765")
console = Console()


def check_status() -> None:
    """Print brain status and exit."""
    try:
        resp = requests.get(f"{BRAIN_URL}/status", timeout=5)
        data = resp.json()
        console.print(f"[bold cyan]Jarvis Brain Status[/bold cyan]")
        console.print(f"  Status: [green]Online[/green]" if data.get("ok") else "  Status: [red]Offline[/red]")
        console.print(f"  Model:  {data.get('model', 'unknown')}")
        console.print(f"  Memory: {data.get('memory_turns', 0)} turns")
    except requests.ConnectionError:
        console.print("[red]Jarvis brain is not running.[/red] Start it with start_brain.ps1")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")
        sys.exit(1)


def reset_memory() -> None:
    """Clear conversation memory after confirmation."""
    console.print("[yellow]This will clear all conversation memory.[/yellow]")
    confirm = input("Are you sure? (yes/no): ").strip().lower()
    if confirm in ("yes", "y"):
        try:
            resp = requests.post(f"{BRAIN_URL}/reset", timeout=5)
            if resp.json().get("ok"):
                console.print("[green]Memory cleared, Sir.[/green]")
            else:
                console.print("[red]Failed to clear memory.[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    else:
        console.print("Reset cancelled.")


def send_message(message: str) -> None:
    """Send a message to the brain and stream the response."""
    try:
        resp = requests.post(
            f"{BRAIN_URL}/chat",
            json={"message": message},
            stream=True,
            timeout=120,
        )
        resp.raise_for_status()
    except requests.ConnectionError:
        console.print("[red]Cannot reach Jarvis brain.[/red] Is it running?")
        return
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    streaming = False
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        # SSE format: "data: {...}"
        if line.startswith("data: "):
            payload = line[6:]
        elif line.startswith("data:"):
            payload = line[5:]
        else:
            continue

        try:
            chunk = json.loads(payload)
        except json.JSONDecodeError:
            continue

        chunk_type = chunk.get("type")

        if chunk_type == "token":
            # Print each token immediately, no newline
            print(chunk.get("content", ""), end="", flush=True)
            streaming = True
        elif chunk_type == "text":
            content = chunk.get("content", "")
            console.print(Text(content, style="cyan"))
        elif chunk_type == "tool_call":
            tool = chunk.get("tool", "")
            args = chunk.get("args", {})
            console.print(Text(f"  [tool: {tool}({json.dumps(args)})]", style="dim"))
        elif chunk_type == "tool_result":
            tool = chunk.get("tool", "")
            result = chunk.get("result", "")
            preview = result[:150] + "..." if len(result) > 150 else result
            console.print(Text(f"  [result: {preview}]", style="dim"))
        elif chunk_type == "done":
            if streaming:
                print()  # final newline after streamed tokens
            break


def main() -> None:
    """Main CLI entry point."""
    # Handle flags
    args = sys.argv[1:]
    if "--status" in args:
        check_status()
        sys.exit(0)
    if "--reset" in args:
        reset_memory()
        sys.exit(0)

    # Check brain is reachable
    try:
        requests.get(f"{BRAIN_URL}/status", timeout=3)
    except requests.ConnectionError:
        console.print("[red]Jarvis brain is not running.[/red] Start it with start_brain.ps1")
        sys.exit(1)

    console.print("[bold cyan]J.A.R.V.I.S.[/bold cyan] — Online and at your service, Sir.")
    console.print("[dim]Type your message. Ctrl+C to exit.[/dim]\n")

    try:
        while True:
            try:
                user_input = input("> ").strip()
            except EOFError:
                break
            if not user_input:
                continue
            send_message(user_input)
            console.print()  # blank line between exchanges
    except KeyboardInterrupt:
        console.print("\n[cyan]Signing off, Sir. Good evening.[/cyan]")
        sys.exit(0)


if __name__ == "__main__":
    main()
