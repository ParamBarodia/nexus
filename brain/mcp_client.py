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

        # External agent bridges: Hermes Agent + multi-model Council
        from brain.tools import call_hermes, council_verify
        self.tools["hermes_delegate"] = {
            "name": "hermes_delegate",
            "description": "Delegate a task to the local Hermes Agent (a separate autonomous agent with 40+ tools running on local models). Use for tasks needing broad tool use or a second autonomous worker.",
            "parameters": {
                "type": "object",
                "properties": {"task": {"type": "string", "description": "The task to delegate to Hermes."}},
                "required": ["task"],
            },
            "handler": lambda task: call_hermes(task),
        }
        self.tools["council_verify"] = {
            "name": "council_verify",
            "description": "Verify a claim, answer, or piece of code with a multi-model Council (several models cross-check to catch bugs/errors). Use when correctness matters and a second opinion is warranted.",
            "parameters": {
                "type": "object",
                "properties": {"content": {"type": "string", "description": "The claim or code to verify."}},
                "required": ["content"],
            },
            "handler": lambda content: council_verify(content),
        }

        # Life-domain tracker: read/update Param's four fronts (research/job_hunt/phd/content)
        from brain.domains import get_domain, get_domains, update_domain, summary as _domains_summary

        def _domain_status(domain=None):
            if domain:
                d = get_domain(domain)
                return json.dumps(d) if d else f"Unknown domain '{domain}'. Use: research, job_hunt, phd, content."
            return _domains_summary() or "No domains tracked."

        self.tools["domain_status"] = {
            "name": "domain_status",
            "description": "Get the current next-action / deadline / staleness for Param's life domains (research, job_hunt, phd, content). Omit 'domain' for a summary of all.",
            "parameters": {
                "type": "object",
                "properties": {"domain": {"type": "string", "description": "research | job_hunt | phd | content (optional)"}},
                "required": [],
            },
            "handler": _domain_status,
        }
        self.tools["domain_update"] = {
            "name": "domain_update",
            "description": "Update a life domain's next action, deadline (YYYY-MM-DD), notes, or status. Use when Param decides or completes the next step on research/job_hunt/phd/content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "research | job_hunt | phd | content"},
                    "next_action": {"type": "string"},
                    "deadline": {"type": "string", "description": "YYYY-MM-DD or empty to clear"},
                    "notes": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["domain"],
            },
            "handler": lambda domain, next_action=None, deadline=None, notes=None, status=None: json.dumps(
                update_domain(domain, next_action, deadline, notes, status)),
        }

        # Persistent WORK AGENTS — dedicated per-topic research/ideation projects.
        import brain.work_agents as wa

        def _work_start(topic, goal=""):
            p = wa.work_start(topic, goal)
            return f"Work project '{p['topic']}' is active, Sir. Next: {p['next_action']}"

        def _work_research_bg(query):
            import threading
            def _job():
                try:
                    wa.work_research(query)
                    from brain.proactive import notify
                    notify(f"Findings folded into the project: {query[:60]}", "Nexus — research done")
                except Exception as e:
                    logger.error("Background research failed: %s", e)
            threading.Thread(target=_job, daemon=True).start()
            return (f"Research on '{query}' started — delegating to Hermes subagents. I'll fold the "
                    f"findings into the work project and notify you when done, Sir.")

        self.tools["work_start"] = {
            "name": "work_start",
            "description": "Start (or resume) a persistent work project on a topic. Use when the user says they want to work on / research / dig into something.",
            "parameters": {"type": "object", "properties": {
                "topic": {"type": "string"}, "goal": {"type": "string"}}, "required": ["topic"]},
            "handler": _work_start,
        }
        self.tools["work_research"] = {
            "name": "work_research",
            "description": "Delegate a web-research task to Hermes (spawns parallel subagents); findings are folded into the active work project. Runs in the background.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"}}, "required": ["query"]},
            "handler": lambda query: _work_research_bg(query),
        }
        self.tools["work_status"] = {
            "name": "work_status",
            "description": "Show the active work project: summary, gaps, ideas, plan, next action.",
            "parameters": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": []},
            "handler": lambda project_id=None: wa.status_text(project_id),
        }
        self.tools["work_idea"] = {
            "name": "work_idea",
            "description": "Record an idea against the active work project.",
            "parameters": {"type": "object", "properties": {"idea": {"type": "string"}}, "required": ["idea"]},
            "handler": lambda idea: ("Noted, Sir." if wa.append_idea(None, idea) else "No active project."),
        }
        self.tools["work_plan"] = {
            "name": "work_plan",
            "description": "Set or update the plan / next action for the active work project.",
            "parameters": {"type": "object", "properties": {
                "plan": {"type": "string"}, "next_action": {"type": "string"}}, "required": []},
            "handler": lambda plan=None, next_action=None: (
                "Updated, Sir." if "error" not in wa.update(None, plan=plan, next_action=next_action) else "No active project."),
        }
        self.tools["work_close"] = {
            "name": "work_close",
            "description": "Close/archive the active work project.",
            "parameters": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": []},
            "handler": lambda project_id=None: str(wa.work_close(project_id)),
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

    def register_external_tools(self, tools: list[dict]):
        """Register tools from external sources (e.g. connectors)."""
        for t in tools:
            if t["name"] not in self.tools:
                self.tools[t["name"]] = t
                logger.info("Registered external tool: %s", t["name"])

    # Tools that BLOCK for a long time (spawn external agents) — excluded from the chat
    # tool-list so a small model can't call them inline and freeze the event loop.
    # They remain available via CLI (/hermes, /verify) and background endpoints.
    CHAT_EXCLUDED = {"hermes_delegate", "council_verify"}

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"]
                }
            } for t in self.tools.values() if t["name"] not in self.CHAT_EXCLUDED
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
