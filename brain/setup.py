"""First-run setup wizard.

Collects the user's profile + life-domains into gitignored *.local.json files
(which take precedence over the shipped templates). Run via:  jarvis --init
"""

import json
from datetime import date
from pathlib import Path

DATA = Path(r"C:\jarvis\data")


def _ask(prompt: str, default: str = "") -> str:
    try:
        v = input(f"{prompt}" + (f" [{default}]" if default else "") + ": ").strip()
    except EOFError:
        v = ""
    return v or default


def run_setup():
    print("\n=== Nexus / J.A.R.V.I.S. — first-run setup ===")
    print("This writes your personal profile to gitignored *.local.json files.")
    print("Press Enter to accept the default shown in [brackets].\n")

    name = _ask("Your full name", "Your Name")
    first = _ask("What JARVIS should call you (first name)", name.split()[0] if name.strip() else "")
    address = _ask("Honorific JARVIS uses", "Sir")
    role = _ask("Your role / title", "")
    city = _ask("Your city", "")
    org = _ask("Your organization", "")
    tone = _ask("Preferred tone", "formal, precise, analytical")
    summary = _ask("One-line summary of who you are", "")

    user = {
        "name": name, "first_name": first, "city": city, "role": role,
        "projects": [], "ambitions": [], "personality_notes": [],
        "preferences": {"address_as": address, "occasional_alt": first, "tone": tone},
    }
    (DATA / "user.local.json").write_text(json.dumps(user, indent=2), encoding="utf-8")

    pctx = {
        "_meta": "Deep context JARVIS silently knows about you. Never recites it.",
        "identity": {"name": name, "role": role, "org": org},
        "background": {"summary": summary},
        "how_to_use": "Weave this in naturally when relevant; never list it back.",
    }
    (DATA / "param_context.local.json").write_text(json.dumps(pctx, indent=2), encoding="utf-8")

    print("\nNow your tracked fronts. Type the single NEXT ACTION for each (Enter to skip):")
    today = date.today().isoformat()
    domains = {}
    for key, label in [("research", "Research"), ("job_hunt", "Job Hunt"),
                       ("phd", "PhD"), ("content", "Content")]:
        na = _ask(f"  {label} — next action", "Define your next action")
        nt = _ask(f"  {label} — short note (optional)", "")
        domains[key] = {"next_action": na, "deadline": None, "notes": nt,
                        "status": "active", "last_updated": today}
    (DATA / "domains.local.json").write_text(json.dumps(domains, indent=2), encoding="utf-8")

    print("\n[OK] Setup complete. Your data: C:\\jarvis\\data\\*.local.json (gitignored).")
    print("Start Nexus:  powershell -File C:\\jarvis\\scripts\\start_nexus.ps1")
    print("Dashboard:    http://localhost:8765/\n")


if __name__ == "__main__":
    run_setup()
