"""Spotify OAuth helper — handles token exchange and auto-refresh.

Setup once:
1. Go to https://developer.spotify.com/dashboard
2. Create App: Name=Nexus, Redirect URI=http://localhost:9876/callback
3. Copy Client ID + Client Secret
4. Run: python brain/connectors/services/spotify_auth.py
5. Browser opens, you login, tokens are saved forever (auto-refresh)
"""

import json
import os
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse

import requests

sys.path.insert(0, r"C:\jarvis")

TOKEN_FILE = Path(r"C:\jarvis\data\spotify_tokens.json")
REDIRECT_URI = "http://localhost:9876/callback"
SCOPES = "user-read-currently-playing user-read-recently-played user-read-playback-state"


def _load_tokens():
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    return {}


def _save_tokens(tokens):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def get_valid_token():
    """Get a valid access token, refreshing if expired. Returns None if not set up."""
    tokens = _load_tokens()
    if not tokens.get("access_token"):
        return None

    # Check if expired
    if time.time() > tokens.get("expires_at", 0) - 60:
        # Refresh
        if not tokens.get("refresh_token") or not tokens.get("client_id"):
            return None
        refreshed = refresh_token(tokens["client_id"], tokens["client_secret"], tokens["refresh_token"])
        if refreshed:
            tokens["access_token"] = refreshed["access_token"]
            tokens["expires_at"] = time.time() + refreshed.get("expires_in", 3600)
            if "refresh_token" in refreshed:
                tokens["refresh_token"] = refreshed["refresh_token"]
            _save_tokens(tokens)
        else:
            return None

    return tokens["access_token"]


def refresh_token(client_id, client_secret, refresh_tok):
    """Refresh an expired access token."""
    try:
        r = requests.post("https://accounts.spotify.com/api/token", data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
            "client_id": client_id,
            "client_secret": client_secret,
        }, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def initial_setup(client_id, client_secret):
    """Run the one-time OAuth flow. Opens browser, catches callback, saves tokens forever."""
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    })

    auth_code = [None]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            auth_code[0] = query.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Nexus: Spotify connected! You can close this tab.</h1>")
        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 9876), Handler)
    print(f"\nOpening browser for Spotify login...")
    webbrowser.open(auth_url)

    print("Waiting for callback...")
    server.handle_request()
    server.server_close()

    if not auth_code[0]:
        print("ERROR: No auth code received.")
        return False

    # Exchange code for tokens
    r = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "authorization_code",
        "code": auth_code[0],
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
    }, timeout=10)

    if r.status_code != 200:
        print(f"ERROR: Token exchange failed: {r.text}")
        return False

    data = r.json()
    tokens = {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": time.time() + data.get("expires_in", 3600),
    }
    _save_tokens(tokens)
    print(f"\nSpotify connected! Tokens saved to {TOKEN_FILE}")
    print("Auto-refresh is enabled — you'll never need to do this again.")
    return True


if __name__ == "__main__":
    print("=== Nexus Spotify Setup ===")
    print("1. Go to: https://developer.spotify.com/dashboard")
    print("2. Create App: Name=Nexus, Redirect URI=http://localhost:9876/callback")
    print("3. Copy Client ID + Client Secret\n")

    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()

    if client_id and client_secret:
        initial_setup(client_id, client_secret)
    else:
        print("Cancelled.")
