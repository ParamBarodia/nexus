"""Project registry and management logic."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

PROJECTS_JSON = Path(r"C:\jarvis\data\projects.json")
logger = logging.getLogger("jarvis.projects")

def _load_data() -> Dict[str, Any]:
    if not PROJECTS_JSON.exists():
        return {"projects": [], "active_project_id": None}
    try:
        return json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    except:
        return {"projects": [], "active_project_id": None}

def _save_data(data: Dict[str, Any]):
    PROJECTS_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")

def list_projects() -> List[Dict[str, Any]]:
    return _load_data().get("projects", [])

def add_project(name: str, path: str, description: str = "") -> bool:
    data = _load_data()
    abs_path = str(Path(path).resolve())
    
    # Check if path already exists
    if any(p["path"] == abs_path for p in data["projects"]):
        logger.warning("Project path already registered: %s", abs_path)
        return False
        
    new_project = {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "path": abs_path,
        "description": description,
        "added_at": datetime.now().isoformat(),
        "last_used": datetime.now().isoformat()
    }
    data["projects"].append(new_project)
    # If no active project, set this as active
    if data["active_project_id"] is None:
        data["active_project_id"] = new_project["id"]
        
    _save_data(data)
    logger.info("Project added: %s at %s", name, abs_path)
    return True

def remove_project(project_id: str) -> bool:
    data = _load_data()
    original_len = len(data["projects"])
    data["projects"] = [p for p in data["projects"] if p["id"] != project_id]
    
    if data["active_project_id"] == project_id:
        data["active_project_id"] = data["projects"][0]["id"] if data["projects"] else None
        
    _save_data(data)
    return len(data["projects"]) < original_len

def set_active(project_id: str) -> bool:
    data = _load_data()
    if any(p["id"] == project_id for p in data["projects"]):
        data["active_project_id"] = project_id
        _save_data(data)
        return True
    return False

def get_active() -> Optional[Dict[str, Any]]:
    data = _load_data()
    for p in data["projects"]:
        if p["id"] == data["active_project_id"]:
            return p
    return None

def scan_project(project_id: str) -> Dict[str, Any]:
    """Return project structure and metadata."""
    data = _load_data()
    project = next((p for p in data["projects"] if p["id"] == project_id), None)
    if not project:
        return {"error": "Project not found"}
        
    root = Path(project["path"])
    if not root.exists():
        return {"error": f"Path {root} does not exist"}
        
    tree = []
    langs = set()
    readme_content = ""
    
    # Simple recursive scan limited to 2 levels for the summary
    for p in root.rglob("*"):
        if any(part in str(p) for part in [".git", "node_modules", "venv", "__pycache__"]):
            continue
            
        if p.is_file():
            if p.suffix in [".py", ".js", ".ts", ".go", ".rs", ".cpp", ".c"]:
                langs.add(p.suffix)
            if p.name.lower() == "readme.md" and not readme_content:
                readme_content = p.read_text(encoding="utf-8")[:1000]
                
        rel = p.relative_to(root)
        if len(rel.parts) <= 2:
            tree.append(str(rel))
            
    return {
        "name": project["name"],
        "path": project["path"],
        "tree_preview": tree[:50],
        "languages": list(langs),
        "readme_excerpt": readme_content
    }
