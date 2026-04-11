"""Indian stocks connector — stock prices and watchlist via yfinance (no API key needed)."""

import os
import logging

from brain.connectors.base import BaseConnector

logger = logging.getLogger("jarvis.connectors.indian_stocks_mf")

DEFAULT_WATCHLIST = "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"


class IndianStocksMFConnector(BaseConnector):
    name = "indian_stocks_mf"
    description = "Indian stocks — prices and watchlist via yfinance"
    category = "markets"
    poll_interval_minutes = 30
    required_env = []

    def _get_watchlist(self) -> list[str]:
        raw = os.getenv("STOCK_WATCHLIST", DEFAULT_WATCHLIST)
        return [s.strip() for s in raw.split(",") if s.strip()]

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "watchlist")

        try:
            import yfinance as yf
        except ImportError:
            return {
                "error": "yfinance package is required. Install with: pip install yfinance",
                "action": action,
                "stocks": [],
            }

        try:
            if action == "price":
                symbol = params.get("symbol", "RELIANCE.NS")
                if not symbol.endswith((".NS", ".BO")):
                    symbol += ".NS"

                cache_key = f"stock_{symbol}"
                cached = self._cache_get(cache_key)
                if cached:
                    return cached

                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="2d")

                price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
                prev_close = info.get("previousClose", 0)
                change = price - prev_close if price and prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0

                data = {
                    "action": "price",
                    "symbol": symbol,
                    "name": info.get("shortName", symbol),
                    "price": round(price, 2) if price else 0,
                    "prev_close": round(prev_close, 2) if prev_close else 0,
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "day_high": info.get("dayHigh", 0),
                    "day_low": info.get("dayLow", 0),
                    "volume": info.get("volume", 0),
                    "market_cap": info.get("marketCap", 0),
                }
                self._cache_set(cache_key, data)
                return data

            else:
                # watchlist
                cached = self._cache_get("stock_watchlist")
                if cached:
                    return cached

                symbols = self._get_watchlist()
                stocks = []
                for symbol in symbols:
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
                        prev_close = info.get("previousClose", 0)
                        change = price - prev_close if price and prev_close else 0
                        change_pct = (change / prev_close * 100) if prev_close else 0
                        stocks.append({
                            "symbol": symbol,
                            "name": info.get("shortName", symbol),
                            "price": round(price, 2) if price else 0,
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                        })
                    except Exception as e:
                        logger.warning("Failed to fetch %s: %s", symbol, e)
                        stocks.append({"symbol": symbol, "name": symbol, "price": 0, "change": 0, "change_pct": 0, "error": str(e)})

                data = {"action": "watchlist", "stocks": stocks}
                self._cache_set("stock_watchlist", data)
                return data

        except Exception as e:
            logger.error("yfinance error: %s", e)
            return {"error": str(e), "action": action, "stocks": []}

    def briefing_summary(self, data: dict) -> str:
        if data.get("error"):
            return f"Stocks: {data['error']}"
        if data.get("action") == "price":
            sign = "+" if data.get("change", 0) >= 0 else ""
            return (
                f"{data.get('name', '')} ({data.get('symbol', '')}): "
                f"Rs {data.get('price', 0)} {sign}{data.get('change', 0)} "
                f"({sign}{data.get('change_pct', 0)}%)"
            )
        stocks = data.get("stocks", [])
        if not stocks:
            return "No stock data available."
        lines = ["Stock Watchlist:"]
        for s in stocks:
            sign = "+" if s.get("change", 0) >= 0 else ""
            lines.append(
                f"  - {s.get('name', s['symbol'])}: Rs {s['price']} "
                f"{sign}{s['change']} ({sign}{s['change_pct']}%)"
            )
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "stock_price",
                "description": "Get current price of an Indian stock (NSE/BSE).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol (e.g. RELIANCE.NS, TCS.NS)"},
                    },
                    "required": ["symbol"],
                },
                "handler": lambda symbol="RELIANCE.NS", **kw: _sync_fetch(
                    self, {"action": "price", "symbol": symbol}
                ),
            },
            {
                "name": "stock_watchlist",
                "description": "Get prices for all stocks in watchlist.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "watchlist"}),
            },
        ]


def _sync_fetch(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
