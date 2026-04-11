"""Notion connector — search pages, list databases, and sync todos/tasks via Notion API."""

import logging
import os

from brain.connectors.base import BaseConnector
from brain.connectors.auth import get_credential

logger = logging.getLogger("jarvis.connectors.notion")

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

_NO_TOKEN_MSG = (
    "Notion API token not configured. "
    "1) Create an integration at https://www.notion.so/my-integrations  "
    "2) Store the token via: brain.connectors.auth.store_credential('notion', 'api_key', '<token>') "
    "   or set the NOTION_TOKEN environment variable."
)


class NotionConnector(BaseConnector):
    name = "notion"
    description = "Notion — search pages, list databases, and sync todos/tasks"
    category = "personal"
    poll_interval_minutes = 30
    required_env = []

    # ------------------------------------------------------------------ auth
    def _get_token(self) -> str:
        token = (
            get_credential("notion", "api_key")
            or get_credential("notion", "bearer_token")
            or os.getenv("NOTION_TOKEN")
        )
        if not token:
            raise RuntimeError(_NO_TOKEN_MSG)
        return token

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ fetch
    async def fetch(self, params=None):
        params = params or {}
        action = params.get("action", "search")

        try:
            token = self._get_token()
        except RuntimeError as e:
            return {"error": str(e), "action": action, "results": []}

        http = await self._get_http()
        headers = self._headers(token)

        try:
            if action == "databases":
                return await self._fetch_databases(http, headers)
            elif action == "todos":
                return await self._fetch_todos(http, headers, params)
            elif action == "add_todo":
                return await self._add_todo(http, headers, params)
            else:
                return await self._fetch_search(http, headers, params)
        except Exception as e:
            logger.error("Notion API error: %s", e)
            return {"action": action, "results": [], "error": str(e)}

    # ---- search
    async def _fetch_search(self, http, headers, params):
        query = params.get("query", "")
        body = {"page_size": 10}
        if query:
            body["query"] = query
        resp = await http.post(f"{NOTION_API}/search", headers=headers, json=body)
        resp.raise_for_status()
        results = []
        for item in resp.json().get("results", []):
            obj_type = item.get("object", "")
            title = _extract_title(item, obj_type)
            results.append({
                "id": item["id"],
                "type": obj_type,
                "title": title or "(Untitled)",
                "url": item.get("url", ""),
            })
        return {"action": "search", "query": query, "results": results}

    # ---- databases
    async def _fetch_databases(self, http, headers):
        cached = self._cache_get("notion_databases")
        if cached:
            return cached
        resp = await http.post(
            f"{NOTION_API}/search",
            headers=headers,
            json={"filter": {"value": "database", "property": "object"}, "page_size": 50},
        )
        resp.raise_for_status()
        results = []
        for db in resp.json().get("results", []):
            title_parts = db.get("title", [])
            title = title_parts[0].get("plain_text", "") if title_parts else "(Untitled)"
            results.append({
                "id": db["id"],
                "title": title,
                "url": db.get("url", ""),
                "properties": list(db.get("properties", {}).keys()),
            })
        data = {"action": "databases", "results": results}
        self._cache_set("notion_databases", data)
        return data

    # ---- todos (incomplete tasks)
    async def _fetch_todos(self, http, headers, params):
        database_id = params.get("database_id")

        # Auto-detect a task database if none provided
        if not database_id:
            database_id = await self._detect_task_database(http, headers)
        if not database_id:
            return {
                "action": "todos",
                "results": [],
                "error": "No database_id provided and could not auto-detect a task database. "
                         "Pass database_id or use notion_databases to find one.",
            }

        # Retrieve database schema to find the right filter property
        schema_resp = await http.get(f"{NOTION_API}/databases/{database_id}", headers=headers)
        schema_resp.raise_for_status()
        db_schema = schema_resp.json()
        props = db_schema.get("properties", {})

        # Build a filter for incomplete tasks
        query_filter = _build_incomplete_filter(props)

        body = {"page_size": 50}
        if query_filter:
            body["filter"] = query_filter

        resp = await http.post(
            f"{NOTION_API}/databases/{database_id}/query",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()

        results = []
        for page in resp.json().get("results", []):
            title = _extract_page_title(page)
            status = _extract_status(page, props)
            results.append({
                "id": page["id"],
                "title": title or "(Untitled)",
                "status": status,
                "url": page.get("url", ""),
                "created": page.get("created_time", ""),
            })
        return {"action": "todos", "database_id": database_id, "results": results}

    # ---- add todo
    async def _add_todo(self, http, headers, params):
        database_id = params.get("database_id")
        title = params.get("title", "")
        if not title:
            return {"action": "add_todo", "error": "title is required", "results": []}

        if not database_id:
            database_id = await self._detect_task_database(http, headers)
        if not database_id:
            return {
                "action": "add_todo",
                "error": "No database_id provided and could not auto-detect a task database.",
                "results": [],
            }

        # Get schema to find the title property name
        schema_resp = await http.get(f"{NOTION_API}/databases/{database_id}", headers=headers)
        schema_resp.raise_for_status()
        db_props = schema_resp.json().get("properties", {})
        title_prop = _find_title_property(db_props)

        new_page = {
            "parent": {"database_id": database_id},
            "properties": {
                title_prop: {
                    "title": [{"text": {"content": title}}],
                },
            },
        }

        resp = await http.post(f"{NOTION_API}/pages", headers=headers, json=new_page)
        resp.raise_for_status()
        page = resp.json()
        return {
            "action": "add_todo",
            "results": [{
                "id": page["id"],
                "title": title,
                "url": page.get("url", ""),
            }],
        }

    # ---- auto-detect a task/todo database
    async def _detect_task_database(self, http, headers):
        db_data = await self._fetch_databases(http, headers)
        for db in db_data.get("results", []):
            db_id = db["id"]
            try:
                resp = await http.get(f"{NOTION_API}/databases/{db_id}", headers=headers)
                resp.raise_for_status()
                props = resp.json().get("properties", {})
                for prop_info in props.values():
                    if prop_info.get("type") in ("checkbox", "status"):
                        return db_id
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------ briefing
    def briefing_summary(self, data: dict) -> str:
        results = data.get("results", [])
        if data.get("error"):
            return f"Notion: {data['error']}"
        if not results:
            return "No Notion results."

        action = data.get("action", "search")

        if action == "todos":
            titles = [r["title"] for r in results]
            count = len(titles)
            listing = ", ".join(titles[:10])
            suffix = f" (and {count - 10} more)" if count > 10 else ""
            return f"{count} pending task{'s' if count != 1 else ''}: {listing}{suffix}"

        if action == "add_todo":
            added = results[0]
            return f"Added todo: {added['title']} ({added.get('url', '')})"

        # search / databases
        lines = [f"Notion {action} ({len(results)} results):"]
        for r in results[:10]:
            tag = f"[{r.get('type', '')}] " if r.get("type") else ""
            lines.append(f"  - {tag}{r['title']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ MCP tools
    def get_mcp_tools(self) -> list[dict]:
        return [
            {
                "name": "notion_search",
                "description": "Search Notion pages and databases.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                },
                "handler": lambda query="", **kw: _sync_fetch(
                    self, {"action": "search", "query": query}
                ),
            },
            {
                "name": "notion_databases",
                "description": "List all Notion databases the integration can access.",
                "parameters": {"type": "object", "properties": {}},
                "handler": lambda **kw: _sync_fetch(self, {"action": "databases"}),
            },
            {
                "name": "notion_todos",
                "description": (
                    "Get incomplete tasks/todos from a Notion database. "
                    "Auto-detects a task database if database_id is omitted."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Notion database ID (optional — auto-detected if omitted)",
                        },
                    },
                },
                "handler": lambda database_id="", **kw: _sync_fetch(
                    self, {"action": "todos", **({"database_id": database_id} if database_id else {})}
                ),
            },
            {
                "name": "notion_add_todo",
                "description": "Add a new task/todo item to a Notion database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title of the new task"},
                        "database_id": {
                            "type": "string",
                            "description": "Notion database ID (optional — auto-detected if omitted)",
                        },
                    },
                    "required": ["title"],
                },
                "handler": lambda title="", database_id="", **kw: _sync_fetch(
                    self,
                    {
                        "action": "add_todo",
                        "title": title,
                        **({"database_id": database_id} if database_id else {}),
                    },
                ),
            },
        ]


# ===================================================================== helpers

def _sync_fetch(connector, params):
    """Synchronous wrapper used by MCP tool handlers."""
    import asyncio
    data = asyncio.run(connector.fetch(params))
    return connector.briefing_summary(data)


def _extract_title(item: dict, obj_type: str) -> str:
    """Extract title from a Notion search result."""
    if obj_type == "page":
        return _extract_page_title(item)
    elif obj_type == "database":
        title_parts = item.get("title", [])
        return title_parts[0].get("plain_text", "") if title_parts else ""
    return ""


def _extract_page_title(page: dict) -> str:
    """Extract the title from a Notion page object."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            if title_parts:
                return title_parts[0].get("plain_text", "")
    return ""


def _find_title_property(db_props: dict) -> str:
    """Return the name of the title property in a database schema."""
    for name, info in db_props.items():
        if info.get("type") == "title":
            return name
    return "Name"  # fallback — most Notion databases use "Name"


def _extract_status(page: dict, schema_props: dict) -> str:
    """Try to read the status/checkbox value from a page."""
    page_props = page.get("properties", {})
    for prop_name, prop_schema in schema_props.items():
        prop_type = prop_schema.get("type")
        page_prop = page_props.get(prop_name, {})
        if prop_type == "status":
            status_obj = page_prop.get("status")
            if status_obj:
                return status_obj.get("name", "")
        elif prop_type == "checkbox":
            val = page_prop.get("checkbox")
            return "Done" if val else "Not done"
    return ""


def _build_incomplete_filter(props: dict) -> dict | None:
    """Build a Notion database query filter for incomplete tasks.

    Looks for the first checkbox or status property and builds a filter
    that excludes completed items.
    """
    for prop_name, prop_info in props.items():
        prop_type = prop_info.get("type")
        if prop_type == "checkbox":
            return {"property": prop_name, "checkbox": {"equals": False}}
        if prop_type == "status":
            # Filter out items whose status is "Done" or "Complete"
            return {
                "and": [
                    {"property": prop_name, "status": {"does_not_equal": "Done"}},
                    {"property": prop_name, "status": {"does_not_equal": "Complete"}},
                ]
            }
    return None
