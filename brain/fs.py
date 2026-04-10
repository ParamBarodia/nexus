"""Scoped file system operations with path validation."""

import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional
from brain.projects import get_active, list_projects

logger = logging.getLogger("jarvis.fs")

def validate_path(path: str, project_id: str = None) -> Optional[Path]:
    """Ensures path resolves inside a registered project root."""
    requested_path = Path(path)
    projects = list_projects()

    if project_id:
        target_proj = next((p for p in projects if p["id"] == project_id), None)
        if target_proj:
            root = Path(target_proj["path"]).resolve()
            if not requested_path.is_absolute():
                requested_path = root / requested_path

    try:
        requested = requested_path.resolve()
    except Exception as e:
        logger.error("Path resolution failed for %s: %s", path, e)
        return None

    # Check against ALL registered projects, not just active one
    for proj in projects:
        root = Path(proj["path"]).resolve()
        if requested.is_relative_to(root):
            return requested
            
    logger.warning("Access denied: path %s is not within any registered project folder.", path)
    return None

def safe_read(path: str, project_id: str = None) -> str:
    valid_path = validate_path(path, project_id)
    if not valid_path:
        return "ERROR: Access denied. Path outside project scope."
    try:
        if not valid_path.is_file():
            return f"ERROR: {path} is not a file."
        return valid_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: Could not read file: {e}"

def safe_write(path: str, content: str, project_id: str = None) -> str:
    valid_path = validate_path(path, project_id)
    if not valid_path:
        return "ERROR: Access denied. Path outside project scope."
    try:
        valid_path.parent.mkdir(parents=True, exist_ok=True)
        valid_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"ERROR: Could not write file: {e}"

def safe_delete(path: str, project_id: str = None) -> str:
    valid_path = validate_path(path, project_id)
    if not valid_path:
        return "ERROR: Access denied. Path outside project scope."
    try:
        if valid_path.is_file():
            valid_path.unlink()
        elif valid_path.is_dir():
            shutil.rmtree(valid_path)
        return f"Successfully deleted {path}"
    except Exception as e:
        return f"ERROR: Could not delete: {e}"

def list_dir(path: str, project_id: str = None) -> List[str]:
    valid_path = validate_path(path, project_id)
    if not valid_path:
        return ["ERROR: Access denied."]
    try:
        if not valid_path.is_dir():
            return [f"ERROR: {path} is not a directory."]
        return [f.name for f in valid_path.iterdir()]
    except Exception as e:
        return [f"ERROR: {e}"]

def tree(path: str, depth: int = 2, project_id: str = None) -> str:
    valid_path = validate_path(path, project_id)
    if not valid_path:
        return "ERROR: Access denied."
    
    def _render(p: Path, d: int) -> List[str]:
        if d < 0: return []
        res = [p.name + "/"]
        try:
            for item in sorted(p.iterdir()):
                if any(x in item.name for x in [".git", "node_modules", "venv", "__pycache__"]):
                    continue
                if item.is_dir():
                    res.extend(["  " + line for line in _render(item, d - 1)])
                else:
                    res.append("  " + item.name)
        except:
            pass
        return res

    return "\n".join(_render(valid_path, depth))
