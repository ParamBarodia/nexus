"""Currency/Forex connector — frankfurter.app API (free, no auth)."""

from brain.connectors.base import BaseConnector


class CurrencyForexConnector(BaseConnector):
    name = "forex"
    description = "Currency exchange rates from Frankfurter (ECB data)"
    category = "markets"
    poll_interval_minutes = 60
    required_env = []

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "rate")
        http = await self._get_http()

        if action == "convert":
            amount = float(params.get("amount", 1))
            frm = params.get("from", "USD")
            to = params.get("to", "INR")
            resp = await http.get(
                "https://api.frankfurter.dev/v1/latest",
                params={"amount": amount, "from": frm, "to": to},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "action": "convert",
                "amount": amount,
                "from": frm,
                "to": to,
                "result": data.get("rates", {}),
                "date": data.get("date", ""),
            }
        else:
            base = params.get("base", "USD")
            symbols = params.get("symbols", "INR,EUR,GBP,JPY")
            resp = await http.get(
                "https://api.frankfurter.dev/v1/latest",
                params={"from": base, "to": symbols},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "action": "rate",
                "base": base,
                "rates": data.get("rates", {}),
                "date": data.get("date", ""),
            }

    def briefing_summary(self, data: dict) -> str:
        if data.get("action") == "convert":
            results = data.get("result", {})
            parts = [f"{data['amount']} {data['from']}"]
            for curr, val in results.items():
                parts.append(f"= {val} {curr}")
            return " ".join(parts)
        rates = data.get("rates", {})
        base = data.get("base", "USD")
        return f"{base}: " + " | ".join(f"{c} {v}" for c, v in rates.items())

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "forex_rate",
                "description": "Get exchange rates. Optional: base currency, target symbols.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "base": {"type": "string", "description": "Base currency (default: USD)"},
                        "symbols": {"type": "string", "description": "Target currencies comma-separated (default: INR,EUR,GBP,JPY)"},
                    },
                },
                "handler": lambda base="USD", symbols="INR,EUR,GBP,JPY", **kw: _sync(self, {"action": "rate", "base": base, "symbols": symbols}),
            },
            {
                "name": "forex_convert",
                "description": "Convert an amount between currencies.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "string", "description": "Amount to convert"},
                        "from": {"type": "string", "description": "Source currency"},
                        "to": {"type": "string", "description": "Target currency"},
                    },
                    "required": ["amount", "from", "to"],
                },
                "handler": lambda amount="1", **kw: _sync(self, {"action": "convert", "amount": amount, "from": kw.get("from", "USD"), "to": kw.get("to", "INR")}),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)
