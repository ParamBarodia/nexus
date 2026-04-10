"""Python client for the WhatsApp Node.js bridge."""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv(r"C:\jarvis\.env")

logger = logging.getLogger("jarvis.whatsapp")

BRIDGE_URL = os.getenv("WHATSAPP_NODE_BRIDGE_URL", "http://localhost:8766")
WHATSAPP_LOG = r"C:\jarvis\logs\whatsapp.log"

# Dedicated log
_wlog = logging.getLogger("jarvis.whatsapp_file")
_fh = logging.FileHandler(WHATSAPP_LOG, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
_wlog.addHandler(_fh)
_wlog.setLevel(logging.INFO)


def is_connected() -> bool:
    """Check if WhatsApp bridge is connected."""
    try:
        resp = requests.get(f"{BRIDGE_URL}/status", timeout=3)
        return resp.json().get("connected", False)
    except Exception:
        return False


def get_status() -> dict:
    """Get full bridge status."""
    try:
        resp = requests.get(f"{BRIDGE_URL}/status", timeout=3)
        return resp.json()
    except Exception as e:
        return {"connected": False, "error": str(e)}


def get_qr() -> str | None:
    """Get QR code string for pairing."""
    try:
        resp = requests.get(f"{BRIDGE_URL}/qr", timeout=3)
        return resp.json().get("qr")
    except Exception:
        return None


def send_message(number: str, message: str) -> str:
    """Send a WhatsApp message via the bridge."""
    try:
        resp = requests.post(
            f"{BRIDGE_URL}/send",
            json={"number": number, "message": message},
            timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            _wlog.info("Sent to %s: %s", number, message[:100])
            return f"Message sent to {number}."
        return f"Send failed: {data.get('error', 'unknown')}"
    except requests.ConnectionError:
        return "WhatsApp bridge is not running."
    except Exception as e:
        return f"Send failed: {e}"
