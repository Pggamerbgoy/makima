"""
TOOL: Smart File Finder
──────────────────────────────────────────────
Finds files fast using fuzzy name matching,
content search, and recency scoring.
No more slow os.walk() on every search.

USAGE in file_manager.py or command_router.py:
    from tools.smart_file_finder import SmartFileFinder
    finder = SmartFileFinder()

    results = finder.find("project report")
    # Returns sorted list of matching file paths
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from datetime import datetime


INDEX_FILE = Path("makima_memory/file_index.json")
INDEXED_ROOTS = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path("."),  # project dir
]
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "$RECYCLE.BIN"}
SEARCHABLE_EXTENSIONS = {
    ".txt", ".md", ".py", ".json", ".csv", ".html",
    ".docx", ".pdf", ".xlsx", ".pptx", ".log"
}
MAX_RESULTS = 10
REINDEX_EVERY_MINUTES = 30


class SmartFileFinder:

    def __init__(self):
        INDEX_FILE.parent.mkdir(exist_ok=True)
        self.index = self._load_index()
        self._maybe_reindex()

    # ── Public API ────────────────────────────────────────────────────────────

    def find(self, query: str, max_results: int = MAX_RESULTS) -> List[Dict]:
        """
        Find files matching query. Returns list of:
        {"path": str, "score": float, "modified": str, "size_kb": float}
        Sorted by relevance score descending.
        """
        query_lower = query.lower()
        scored = []

        for path_str, meta in self.index.get("files", {}).items():
            score = self._score(query_lower, path_str, meta)
            if score > 0.2:
                scored.append({
                    "path": path_str,
                    "score": round(score, 3),
                    "modified": meta.get("modified", ""),
                    "size_kb": meta.get("size_kb", 0),
                    "name": Path(path_str).name
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:max_results]

    def find_recent(self, hours: int = 24, extension: str = None) -> List[Dict]:
        """Get files modified in the last N hours."""
        cutoff = time.time() - (hours * 3600)
        results = []

        for path_str, meta in self.index.get("files", {}).items():
            if meta.get("mtime", 0) >= cutoff:
                if extension and not path_str.endswith(extension):
                    continue
                results.append({
                    "path": path_str,
                    "name": Path(path_str).name,
                    "modified": meta.get("modified", ""),
                    "size_kb": meta.get("size_kb", 0)
                })

        results.sort(key=lambda x: x["modified"], reverse=True)
        return results[:MAX_RESULTS]

    def reindex(self, roots: List[Path] = None):
        """Rebuild the file index. Run when file system changes."""
        print("[FileFinder] Indexing files...")
        roots = roots or INDEXED_ROOTS
        files = {}
        count = 0

        for root in roots:
            if not root.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip junk directories
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

                for fname in filenames:
                    fpath = Path(dirpath) / fname
                    if fpath.suffix.lower() not in SEARCHABLE_EXTENSIONS:
                        continue
                    try:
                        stat = fpath.stat()
                        files[str(fpath)] = {
                            "name": fname.lower(),
                            "stem": fpath.stem.lower(),
                            "ext": fpath.suffix.lower(),
                            "mtime": stat.st_mtime,
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                            "size_kb": round(stat.st_size / 1024, 1)
                        }
                        count += 1
                    except (PermissionError, OSError):
                        continue

        self.index = {
            "files": files,
            "built_at": time.time(),
            "count": count
        }
        self._save_index()
        print(f"[FileFinder] Indexed {count} files")

    def add_to_index(self, path: str):
        """Manually add a single file to the index."""
        p = Path(path)
        if p.exists():
            stat = p.stat()
            self.index.setdefault("files", {})[path] = {
                "name": p.name.lower(),
                "stem": p.stem.lower(),
                "ext": p.suffix.lower(),
                "mtime": stat.st_mtime,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size_kb": round(stat.st_size / 1024, 1)
            }
            self._save_index()

    def stats(self) -> Dict:
        built = self.index.get("built_at", 0)
        age_min = round((time.time() - built) / 60, 1) if built else None
        return {
            "files_indexed": self.index.get("count", 0),
            "index_age_minutes": age_min
        }

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score(self, query: str, path_str: str, meta: Dict) -> float:
        score = 0.0
        name = meta.get("name", "")
        stem = meta.get("stem", "")

        # Exact filename match
        if query == stem:
            score += 1.0
        elif query in name:
            score += 0.8

        # Fuzzy filename match
        fuzzy = SequenceMatcher(None, query, stem).ratio()
        score += fuzzy * 0.5

        # Query words in path
        words = query.split()
        path_lower = path_str.lower()
        word_hits = sum(1 for w in words if w in path_lower)
        score += (word_hits / max(len(words), 1)) * 0.4

        # Recency bonus (files modified recently rank higher)
        age_days = (time.time() - meta.get("mtime", 0)) / 86400
        if age_days < 1:
            score += 0.3
        elif age_days < 7:
            score += 0.15
        elif age_days < 30:
            score += 0.05

        return score

    # ── Index management ──────────────────────────────────────────────────────

    def _maybe_reindex(self):
        built = self.index.get("built_at", 0)
        age_minutes = (time.time() - built) / 60
        if age_minutes > REINDEX_EVERY_MINUTES or not self.index.get("files"):
            import threading
            t = threading.Thread(target=self.reindex, daemon=True)
            t.start()

    def _load_index(self) -> Dict:
        if INDEX_FILE.exists():
            try:
                return json.loads(INDEX_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _save_index(self):
        INDEX_FILE.write_text(json.dumps(self.index, indent=2))
