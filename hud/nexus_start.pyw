"""Nexus unified startup — launches brain server, speaks greeting, opens HUD.
.pyw extension = no console window on Windows.
"""

import subprocess
import sys
import time
import os
import threading

VENV_PYTHON = r"C:\jarvis\venv\Scripts\pythonw.exe"
VENV_PYTHON_CONSOLE = r"C:\jarvis\venv\Scripts\python.exe"
JARVIS_DIR = r"C:\jarvis"


def start_brain():
    """Start the brain server in background."""
    subprocess.Popen(
        [VENV_PYTHON_CONSOLE, "-m", "uvicorn", "brain.server:app",
         "--host", "127.0.0.1", "--port", "8765", "--log-level", "info"],
        cwd=JARVIS_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_brain(max_wait=30):
    """Wait until brain responds."""
    import requests
    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = requests.get("http://localhost:8765/status", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def run_greeting():
    """Run the voice greeting in a separate process (needs console for audio)."""
    subprocess.Popen(
        [VENV_PYTHON_CONSOLE, os.path.join(JARVIS_DIR, "hud", "startup_greeting.py")],
        cwd=JARVIS_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def run_hud():
    """Launch the HUD overlay."""
    subprocess.Popen(
        [VENV_PYTHON, os.path.join(JARVIS_DIR, "hud", "overlay.py")],
        cwd=JARVIS_DIR,
    )


if __name__ == "__main__":
    # 1. Start brain server
    start_brain()

    # 2. Wait for it to be ready
    wait_for_brain(30)

    # 3. Launch greeting (async, runs in background)
    run_greeting()

    # 4. Small delay then launch HUD
    time.sleep(2)
    run_hud()
