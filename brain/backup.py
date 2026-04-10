"""Backup and export system for Nexus sovereignty."""

import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.backup")

JARVIS_ROOT = Path(r"C:\jarvis")
BACKUP_DIR = JARVIS_ROOT / "data" / "backups"
EXPORT_DIR = JARVIS_ROOT / "data" / "exports"

# Files/dirs to back up
BACKUP_TARGETS = [
    JARVIS_ROOT / "data" / "user.json",
    JARVIS_ROOT / "data" / "memory.json",
    JARVIS_ROOT / "data" / "projects.json",
    JARVIS_ROOT / "data" / "hooks.json",
    JARVIS_ROOT / "data" / "chroma",
    JARVIS_ROOT / "data" / "chroma_knowledge",
    JARVIS_ROOT / ".env",
]

MAX_DAILY_BACKUPS = 7
MAX_WEEKLY_EXPORTS = 4


def backup_all() -> str:
    """Create a timestamped zip backup of all Nexus state."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    zip_path = BACKUP_DIR / f"nexus_{ts}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for target in BACKUP_TARGETS:
            if not target.exists():
                continue
            if target.is_file():
                arcname = target.relative_to(JARVIS_ROOT)
                zf.write(target, arcname)
            elif target.is_dir():
                for root, _dirs, files in os.walk(target):
                    for f in files:
                        fpath = Path(root) / f
                        arcname = fpath.relative_to(JARVIS_ROOT)
                        zf.write(fpath, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    logger.info("Backup created: %s (%.2f MB)", zip_path.name, size_mb)

    # Prune old daily backups
    _prune_old(BACKUP_DIR, MAX_DAILY_BACKUPS)

    return f"Backup created: {zip_path.name} ({size_mb:.2f} MB)"


def export_human_readable() -> str:
    """Export all memories and conversations as markdown."""
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    export_path = EXPORT_DIR / ts
    export_path.mkdir(parents=True, exist_ok=True)

    # Export user profile
    user_json = JARVIS_ROOT / "data" / "user.json"
    if user_json.exists():
        profile = json.loads(user_json.read_text(encoding="utf-8"))
        md = "# User Profile\n\n"
        for k, v in profile.items():
            if isinstance(v, list):
                md += f"## {k}\n" + "\n".join(f"- {item}" for item in v) + "\n\n"
            elif isinstance(v, dict):
                md += f"## {k}\n" + "\n".join(f"- **{sk}**: {sv}" for sk, sv in v.items()) + "\n\n"
            else:
                md += f"- **{k}**: {v}\n"
        (export_path / "user_profile.md").write_text(md, encoding="utf-8")

    # Export conversation memory
    memory_json = JARVIS_ROOT / "data" / "memory.json"
    if memory_json.exists():
        entries = json.loads(memory_json.read_text(encoding="utf-8"))
        md = "# Conversation History\n\n"
        for e in entries:
            role = e.get("role", "unknown").upper()
            content = e.get("content", "")
            ts_str = e.get("timestamp", "")
            md += f"### {role} ({ts_str})\n{content}\n\n---\n\n"
        (export_path / "conversations.md").write_text(md, encoding="utf-8")

    # Export Mem0 memories
    try:
        from brain.memory_mem0 import get_all_memories
        all_mems = get_all_memories()
        if all_mems:
            md = "# Long-term Memories (Mem0)\n\n"
            for i, m in enumerate(all_mems, 1):
                if isinstance(m, dict):
                    md += f"{i}. {m.get('memory', str(m))}\n"
                else:
                    md += f"{i}. {m}\n"
            (export_path / "mem0_memories.md").write_text(md, encoding="utf-8")
    except Exception as e:
        logger.warning("Could not export Mem0 memories: %s", e)

    # Export projects
    projects_json = JARVIS_ROOT / "data" / "projects.json"
    if projects_json.exists():
        data = json.loads(projects_json.read_text(encoding="utf-8"))
        md = "# Registered Projects\n\n"
        for p in data.get("projects", []):
            md += f"## {p['name']}\n- ID: {p['id']}\n- Path: {p['path']}\n- Added: {p.get('added_at', 'unknown')}\n\n"
        (export_path / "projects.md").write_text(md, encoding="utf-8")

    # Prune old exports
    _prune_old(EXPORT_DIR, MAX_WEEKLY_EXPORTS)

    file_count = len(list(export_path.glob("*.md")))
    logger.info("Export created: %s (%d files)", export_path.name, file_count)
    return f"Export created: {export_path.name} ({file_count} markdown files)"


def list_backups() -> list[dict]:
    """List all backups with metadata."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = []
    for f in sorted(BACKUP_DIR.glob("nexus_*.zip"), reverse=True):
        backups.append({
            "name": f.name,
            "path": str(f),
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return backups


def restore_from_backup(zip_path: str) -> str:
    """Restore Nexus state from a backup zip."""
    zp = Path(zip_path)
    if not zp.exists():
        return f"ERROR: Backup file not found: {zip_path}"
    if not zp.suffix == ".zip":
        return f"ERROR: Not a zip file: {zip_path}"

    # Extract to jarvis root, overwriting existing files
    with zipfile.ZipFile(zp, "r") as zf:
        zf.extractall(JARVIS_ROOT)

    logger.info("Restored from backup: %s", zp.name)
    return f"Restored from {zp.name}. Restart the brain to apply changes."


def _prune_old(directory: Path, keep: int) -> None:
    """Keep only the N most recent items in a directory."""
    items = sorted(directory.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in items[keep:]:
        if old.is_file():
            old.unlink()
        elif old.is_dir():
            shutil.rmtree(old)
        logger.info("Pruned old: %s", old.name)
