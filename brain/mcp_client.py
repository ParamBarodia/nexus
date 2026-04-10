"""MCP client for tool discovery and execution."""

import json
import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger("jarvis.mcp")

# This is a simplified MCP manager for Nexus
class MCPManager:
    def __init__(self):
        self.tools = {}
        # Internal Phase 0 tools migrated to MCP format
        self.register_builtin_tools()

    def register_builtin_tools(self):
        # We define them here to match the MCP schema expectations
        self.tools["get_time"] = {
            "name": "get_time",
            "description": "Return current date and time.",
            "parameters": {"type": "object", "properties": {}},
            "handler": self._get_time
        }
        self.tools["web_search"] = {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            },
            "handler": self._web_search
        }
        
        # Filesystem Tools
        from brain.fs import safe_read, safe_write, safe_delete, list_dir, tree
        from brain.projects import scan_project, list_projects
        
        fs_tools = [
            ("read_file", "Read content of a file within a project.", safe_read, ["path"]),
            ("write_file", "Write content to a file (ask confirmation first).", safe_write, ["path", "content"]),
            ("delete_file", "Delete a file or directory (ask confirmation first).", safe_delete, ["path"]),
            ("list_dir", "List contents of a directory.", list_dir, ["path"]),
            ("project_tree", "Show file tree of a project path.", tree, ["path"]),
            ("scan_project", "Scan a project for structure and README.", scan_project, ["project_id"]),
            ("list_projects", "List all registered projects.", list_projects, [])
        ]
        
        for name, desc, handler, req in fs_tools:
            self.tools[name] = {
                "name": name,
                "description": desc,
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "project_id": {"type": "string"}
                    },
                    "required": req
                },
                "handler": handler
            }

        # Code Execution
        from brain.code_exec import run_python
        self.tools["run_python"] = {
            "name": "run_python",
            "description": "Execute Python code and return results (ask confirmation first).",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"]
            },
            "handler": run_python
        }
        
        # Knowledge Recall
        from brain.knowledge import recall
        self.tools["recall"] = {
            "name": "recall",
            "description": "Search for relevant knowledge/code chunks from registered projects.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            },
            "handler": recall
        }

        # Real WhatsApp tool (replaces stub if bridge available)
        from brain.whatsapp.client import send_message as wa_send, is_connected as wa_connected
        self.tools["whatsapp_send"] = {
            "name": "whatsapp_send",
            "description": "Send a WhatsApp message to a phone number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "string", "description": "Phone number with country code (e.g. +91...)"},
                    "message": {"type": "string", "description": "Message text to send"},
                },
                "required": ["number", "message"],
            },
            "handler": lambda number, message: wa_send(number, message) if wa_connected() else "WhatsApp bridge is not running.",
        }

        # Load India MCP Servers (will skip whatsapp_send stub since we already registered the real one)
        self._load_india_mcp()

    def _load_india_mcp(self):
        import importlib.util
        path = r"C:\jarvis\brain\mcp_servers_india"
        for filename in os.listdir(path):
            if filename.endswith(".py") and filename != "__init__.py":
                mod_name = f"brain.mcp_servers_india.{filename[:-3]}"
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(path, filename))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "get_service"):
                        svc = mod.get_service()
                        self.tools[svc["name"]] = svc
                        logger.info("Loaded India MCP: %s", svc["name"])
                except Exception as e:
                    logger.error("Failed to load India MCP %s: %s", mod_name, e)

    def _get_time(self, **kwargs):
        from datetime import datetime
        return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    def _web_search(self, query: str):
        """Tavily first (if key set), DDG fallback."""
        import os
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        if tavily_key:
            try:
                from tavily import TavilyClient
                client = TavilyClient(api_key=tavily_key)
                resp = client.search(query, max_results=5, search_depth="basic")
                parts = []
                if resp.get("answer"):
                    parts.append(f"Summary: {resp['answer']}")
                for r in resp.get("results", [])[:5]:
                    parts.append(f"{r.get('title', '')}: {r.get('content', '')}")
                if parts:
                    return "\n\n".join(parts)[:3000]
            except Exception as e:
                logger.warning("Tavily search failed, falling back to DDG: %s", e)
        from brain.tools import web_search
        return web_search(query)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"]
                }
            } for t in self.tools.values()
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        if name not in self.tools:
            return f"Error: Tool {name} not found."
        try:
            handler = self.tools[name]["handler"]
            result = handler(**arguments)
            return str(result)
        except Exception as e:
            logger.error("MCP Tool %s failed: %s", name, e)
            return f"Error: Tool execution failed: {e}"

# Global instance
mcp = MCPManager()
