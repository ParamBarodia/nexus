"""arXiv connector — arxiv.org API (free, no auth)."""

import xml.etree.ElementTree as ET

from brain.connectors.base import BaseConnector


class ArxivConnector(BaseConnector):
    name = "arxiv"
    description = "Search and browse recent arXiv papers"
    category = "dev"
    poll_interval_minutes = 720
    required_env = []

    _NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}

    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "search")
        http = await self._get_http()

        if action == "recent":
            category = params.get("category", "cs.AI")
            query = f"cat:{category}"
        else:
            query = params.get("query", "large language models")

        resp = await http.get(
            "https://export.arxiv.org/api/query",
            params={"search_query": query, "start": 0, "max_results": 10, "sortBy": "submittedDate", "sortOrder": "descending"},
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        ns = self._NAMESPACE
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            summary = entry.findtext("atom:summary", "", ns).strip()[:200]
            link = ""
            for lnk in entry.findall("atom:link", ns):
                if lnk.get("type") == "text/html":
                    link = lnk.get("href", "")
                    break
            if not link:
                link = entry.findtext("atom:id", "", ns)
            authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]
            papers.append({
                "title": title,
                "authors": authors[:3],
                "summary": summary,
                "url": link,
            })

        return {"query": query, "papers": papers}

    def briefing_summary(self, data: dict) -> str:
        papers = data.get("papers", [])[:3]
        if not papers:
            return "No recent arXiv papers found."
        lines = ["Recent arXiv papers:"]
        for p in papers:
            lines.append(f"  - {p['title']} ({', '.join(p['authors'][:2])})")
        return "\n".join(lines)

    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "arxiv_search",
                "description": "Search arXiv for papers.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query"}},
                    "required": ["query"],
                },
                "handler": lambda query="LLM", **kw: _sync(self, {"action": "search", "query": query}),
            },
            {
                "name": "arxiv_recent",
                "description": "Get recent arXiv papers in a category (default: cs.AI).",
                "parameters": {
                    "type": "object",
                    "properties": {"category": {"type": "string", "description": "arXiv category (e.g. cs.AI, q-bio.NC)"}},
                },
                "handler": lambda category="cs.AI", **kw: _sync(self, {"action": "recent", "category": category}),
            },
        ]


def _sync(connector, params):
    import asyncio
    data = asyncio.run(connector.fetch(params))
    papers = data.get("papers", [])
    if not papers:
        return "No papers found."
    return "\n".join(f"- {p['title']}\n  {p['url']}" for p in papers)
