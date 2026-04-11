"""CoinGecko crypto connector — free API, no auth required."""

import os

from brain.connectors.base import BaseConnector


class CryptoCoingeckoConnector(BaseConnector):
    name = "crypto"
    description = "Cryptocurrency prices and trending coins from CoinGecko"
    category = "markets"
    poll_interval_minutes = 30
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "price")
        http = await self._get_http()

        if action == "trending":
            resp = await http.get("https://api.coingecko.com/api/v3/search/trending")
            resp.raise_for_status()
            coins = resp.json().get("coins", [])
            return {
                "action": "trending",
                "coins": [
                    {"name": c["item"]["name"], "symbol": c["item"]["symbol"],
                     "rank": c["item"].get("market_cap_rank")}
                    for c in coins[:10]
                ],
            }
        else:
            watchlist = params.get("ids") or os.getenv("CRYPTO_WATCHLIST", "bitcoin,ethereum,solana")
            resp = await http.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": watchlist, "vs_currencies": "usd,inr", "include_24hr_change": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
            prices = {}
            for coin_id, info in data.items():
                prices[coin_id] = {
                    "usd": info.get("usd"),
                    "inr": info.get("inr"),
                    "change_24h": info.get("usd_24h_change"),
                }
            return {"action": "price", "prices": prices}

    def briefing_summary(self, data: dict) -> str:
        if data.get("action") == "trending":
            coins = data.get("coins", [])[:5]
            return "Trending crypto: " + ", ".join(f"{c['name']} ({c['symbol']})" for c in coins)
        prices = data.get("prices", {})
        if not prices:
            return "No crypto price data available."
        lines = []
        for coin, info in prices.items():
            change = info.get("change_24h")
            arrow = "↑" if change and change > 0 else "↓"
            lines.append(f"{coin}: ${info['usd']:,.2f} {arrow}{abs(change or 0):.1f}%")
        return "Crypto: " + " | ".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "crypto_price",
                "description": "Get cryptocurrency prices. Pass comma-separated coin IDs (e.g. bitcoin,ethereum).",
                "parameters": {
                    "type": "object",
                    "properties": {"ids": {"type": "string", "description": "Comma-separated coin IDs"}},
                },
                "handler": lambda ids=None, **kw: _sync(self, {"action": "price", "ids": ids}),
            },
            {
                "name": "crypto_trending",
                "description": "Get trending cryptocurrencies on CoinGecko.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync(self, {"action": "trending"}),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
