"""Knowledge ingestion (RAG) and document indexing with ChromaDB."""

import logging
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import chromadb
from chromadb.utils import embedding_functions
from brain.projects import list_projects

logger = logging.getLogger("jarvis.knowledge")

CHROMA_PATH = r"C:\jarvis\data\chroma_knowledge"
client = chromadb.PersistentClient(path=CHROMA_PATH)
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Dedicated collection for project knowledge
collection = client.get_or_create_collection(
    name="project_knowledge",
    embedding_function=embedding_fn
)

class ProjectWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            index_file(Path(event.src_path))
    def on_created(self, event):
        if not event.is_directory:
            index_file(Path(event.src_path))

def index_file(path: Path):
    """Index a single file into ChromaDB."""
    if any(part in str(path) for part in [".git", "node_modules", "venv", "__pycache__", "dist", "build"]):
        return
    
    if path.suffix not in [".md", ".txt", ".py", ".js", ".ts", ".go", ".rs"]:
        return

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if not content.strip(): return
        
        # Split into chunks (simple approach)
        chunks = [content[i:i+2000] for i in range(0, len(content), 1500)]
        
        ids = [f"{path}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": str(path)} for _ in chunks]
        
        collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metadatas
        )
        logger.info("Indexed %s (%d chunks)", path.name, len(chunks))
    except Exception as e:
        logger.error("Failed to index %s: %s", path, e)

def recall(query: str, n_results: int = 5):
    """Search for relevant knowledge chunks."""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        # Format results for the LLM
        formatted = []
        for i in range(len(results["documents"][0])):
            doc = results["documents"][0][i]
            meta = results["metadatas"][0][i]
            source = meta.get("source", "Unknown")
            formatted.append(f"Source: {source}\nContent: {doc}")
        return "\n\n---\n\n".join(formatted)
    except Exception as e:
        logger.error("Recall failed: %s", e)
        return "No relevant knowledge found."

def start_watchers():
    """Start watchdog observers for all registered projects."""
    projects = list_projects()
    observer = Observer()
    for proj in projects:
        root = Path(proj["path"])
        if root.exists():
            # Initial full scan
            for p in root.rglob("*"):
                if p.is_file(): index_file(p)
            # Start watching
            observer.schedule(ProjectWatcher(), str(root), recursive=True)
            logger.info("Watching project: %s", proj["name"])
    observer.start()
    return observer
