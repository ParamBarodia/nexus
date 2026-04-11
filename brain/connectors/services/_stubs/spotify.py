"""Spotify connector stub.

API URL : https://api.spotify.com/v1/
Auth     : OAuth2
Env vars : SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
Category : personal
"""

from brain.connectors.base import BaseConnector


class SpotifyConnector(BaseConnector):
    name = "spotify"
    description = "Currently playing, recent tracks, and top artists from Spotify"
    category = "personal"
    required_env = ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement Spotify API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
