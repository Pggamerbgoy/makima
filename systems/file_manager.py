"""
systems/file_manager.py

Natural Language File Manager
───────────────────────────────
Find, move, rename, delete, and organize files by describing them in plain English.

Commands:
  "Find my resume"
  "Find all PDFs from last week"
  "Move my screenshots to Desktop"
  "Rename the file called report to final_report"
  "Delete temp files older than 30 days"
  "Show me what's in my Downloads"
  "Organize my Downloads folder"
  "Find large files bigger than 100MB"
  "Find files I edited today"
"""

import os
import re
import time
import shutil
import logging
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("Makima.FileManager")
OS = platform.system()

# Common folder aliases
FOLDER_ALIASES = {
    "desktop": Path.home() / "Desktop",
    "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "pictures": Path.home() / "Pictures",
    "music": Path.home() / "Music",
    "videos": Path.home() / "Videos",
    "home": Path.home(),
}

# File type mappings
EXTENSION_MAP = {
    "pdf": [".pdf"],
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
    "video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
    "document": [".doc", ".docx", ".odt", ".txt", ".rtf"],
    "spreadsheet": [".xls", ".xlsx", ".csv", ".ods"],
    "code": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".go", ".rs"],
    "archive": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "screenshot": [".png", ".jpg"],  # filtered by name below
    "temp": [".tmp", ".temp", ".bak", ".log"],
}


def _resolve_folder(name: str) -> Optional[Path]:
    """Resolve common folder names to absolute paths."""
    name_lower = name.lower().strip()
    for alias, path in FOLDER_ALIASES.items():
        if alias in name_lower:
            return path
    # Check if it's a valid absolute path
    p = Path(name)
    if p.exists():
        return p
    return None


def _human_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class FileManager:
    """Natural language file operations with AI intent parsing."""

    DEFAULT_SEARCH_ROOT = Path.home()
    MAX_RESULTS = 10

    def __init__(self, ai):
        self.ai = ai
        self._last_results: list[Path] = []

    # ─── Finding ──────────────────────────────────────────────────────────────

    def find(self, query: str) -> str:
        """Natural language file search."""
        query_lower = query.lower()

        # Determine search root
        search_root = self.DEFAULT_SEARCH_ROOT
        for alias, path in FOLDER_ALIASES.items():
            if alias in query_lower:
                search_root = path
                break

        # Determine file type filter
        extensions = []
        for ftype, exts in EXTENSION_MAP.items():
            if ftype in query_lower:
                extensions = exts
                break

        # Determine time filter
        days_filter = None
        if "today" in query_lower:
            days_filter = 0
        elif "yesterday" in query_lower:
            days_filter = 1
        elif "last week" in query_lower:
            days_filter = 7
        elif "last month" in query_lower:
            days_filter = 30

        # Size filter
        size_min = None
        size_match = re.search(r"bigger than (\d+)\s*(mb|gb|kb)", query_lower)
        if size_match:
            amount = int(size_match.group(1))
            unit = size_match.group(2)
            mult = {"kb": 1024, "mb": 1024**2, "gb": 1024**3}[unit]
            size_min = amount * mult

        # Name keyword (extract non-keyword words)
        stop_words = {"find", "search", "my", "the", "a", "an", "all", "from",
                      "in", "on", "to", "files", "folder", "documents", "pdf",
                      "image", "video", "audio", "code", "bigger", "than",
                      "today", "yesterday", "last", "week", "month", "old"}
        name_keywords = [w for w in query_lower.split() if w not in stop_words and len(w) > 2]

        results = self._search(
            root=search_root,
            name_keywords=name_keywords,
            extensions=extensions,
            days_filter=days_filter,
            size_min=size_min,
        )

        if not results:
            return f"No files found matching your description."

        self._last_results = results[:self.MAX_RESULTS]
        lines = []
        for i, p in enumerate(self._last_results, 1):
            size = _human_size(p.stat().st_size) if p.is_file() else "folder"
            modified = datetime.fromtimestamp(p.stat().st_mtime).strftime("%b %d")
            lines.append(f"{i}. {p.name} ({size}, {modified}) — {p.parent}")

        return f"Found {len(results)} file(s):\n" + "\n".join(lines[:self.MAX_RESULTS])

    def _search(self, root: Path, name_keywords: list, extensions: list,
                days_filter: Optional[int], size_min: Optional[int]) -> list[Path]:
        results = []
        cutoff_time = None
        if days_filter is not None:
            cutoff_time = time.time() - (days_filter + 1) * 86400

        try:
            for p in root.rglob("*"):
                # Skip hidden dirs
                if any(part.startswith(".") for part in p.parts):
                    continue
                if not p.is_file():
                    continue

                # Extension filter
                if extensions and p.suffix.lower() not in extensions:
                    continue

                # Name keyword filter
                if name_keywords:
                    name_lower = p.name.lower()
                    if not any(kw in name_lower for kw in name_keywords):
                        continue

                # Time filter
                if cutoff_time is not None:
                    if p.stat().st_mtime < cutoff_time:
                        continue

                # Size filter
                if size_min is not None:
                    if p.stat().st_size < size_min:
                        continue

                results.append(p)
                if len(results) >= 50:  # Cap search results
                    break
        except PermissionError:
            pass

        # Sort by modification time (newest first)
        results.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return results

    # ─── Moving ───────────────────────────────────────────────────────────────

    def move(self, source_desc: str, dest_desc: str) -> str:
        dest = _resolve_folder(dest_desc)
        if not dest:
            return f"I don't recognize '{dest_desc}' as a folder."

        if not dest.exists():
            return f"Destination folder doesn't exist: {dest}"

        # Check if we have recent search results
        if self._last_results and any(kw in source_desc.lower()
                                       for kw in ["them", "those", "these", "it", "the files"]):
            moved = 0
            for f in self._last_results:
                try:
                    shutil.move(str(f), str(dest / f.name))
                    moved += 1
                except Exception as e:
                    logger.warning(f"Move error: {e}")
            return f"Moved {moved} files to {dest.name}."

        # Otherwise search and move
        keywords = [w for w in source_desc.lower().split()
                    if w not in {"move", "my", "the", "all", "files", "to"}]
        results = self._search(root=self.DEFAULT_SEARCH_ROOT,
                               name_keywords=keywords, extensions=[],
                               days_filter=None, size_min=None)
        if not results:
            return f"No files found matching '{source_desc}'."

        moved = 0
        for f in results[:20]:  # Safety cap
            try:
                shutil.move(str(f), str(dest / f.name))
                moved += 1
            except Exception as e:
                logger.warning(f"Move error: {e}")
        return f"Moved {moved} file(s) to {dest.name}."

    # ─── Renaming ─────────────────────────────────────────────────────────────

    def rename(self, old_name: str, new_name: str) -> str:
        keywords = old_name.lower().split()
        results = self._search(root=self.DEFAULT_SEARCH_ROOT,
                               name_keywords=keywords, extensions=[],
                               days_filter=None, size_min=None)
        if not results:
            return f"Couldn't find a file called '{old_name}'."

        target = results[0]
        new_path = target.parent / (new_name + target.suffix)
        try:
            target.rename(new_path)
            return f"Renamed '{target.name}' to '{new_path.name}'."
        except Exception as e:
            return f"Rename failed: {e}"

    # ─── Organization ─────────────────────────────────────────────────────────

    def organize_folder(self, folder_name: str) -> str:
        """Auto-organize a folder by file type into subfolders."""
        folder = _resolve_folder(folder_name)
        if not folder or not folder.exists():
            return f"Can't find folder: {folder_name}"

        TYPE_FOLDERS = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".odt"],
            "Audio": [".mp3", ".wav", ".flac", ".aac"],
            "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
            "Code": [".py", ".js", ".html", ".css", ".java"],
            "Spreadsheets": [".xls", ".xlsx", ".csv"],
        }

        ext_to_folder = {}
        for folder_type, exts in TYPE_FOLDERS.items():
            for ext in exts:
                ext_to_folder[ext] = folder_type

        moved = 0
        for item in folder.iterdir():
            if not item.is_file():
                continue
            dest_type = ext_to_folder.get(item.suffix.lower(), "Other")
            dest_dir = folder / dest_type
            dest_dir.mkdir(exist_ok=True)
            try:
                shutil.move(str(item), str(dest_dir / item.name))
                moved += 1
            except Exception as e:
                logger.warning(f"Organize move error: {e}")

        return f"Organized {moved} files in {folder.name} into subfolders."

    # ─── Listing ──────────────────────────────────────────────────────────────

    def list_folder(self, folder_name: str) -> str:
        folder = _resolve_folder(folder_name)
        if not folder or not folder.exists():
            return f"Can't find folder: {folder_name}"

        items = list(folder.iterdir())
        if not items:
            return f"{folder.name} is empty."

        files = [i for i in items if i.is_file()]
        dirs = [i for i in items if i.is_dir()]

        result = f"{folder.name}: {len(files)} files, {len(dirs)} folders.\n"
        for d in sorted(dirs)[:5]:
            result += f"📁 {d.name}/\n"
        for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:8]:
            size = _human_size(f.stat().st_size)
            result += f"📄 {f.name} ({size})\n"
        return result.strip()

    # ─── Delete ───────────────────────────────────────────────────────────────

    def delete_old_files(self, folder_name: str, days: int) -> str:
        folder = _resolve_folder(folder_name) or self.DEFAULT_SEARCH_ROOT
        cutoff = time.time() - days * 86400
        deleted = 0
        freed = 0
        for f in folder.rglob("*"):
            if f.is_file() and f.stat().st_mtime < cutoff:
                if f.suffix.lower() in [".tmp", ".temp", ".bak", ".log"]:
                    try:
                        freed += f.stat().st_size
                        f.unlink()
                        deleted += 1
                    except Exception:
                        pass
        return f"Deleted {deleted} temp files older than {days} days. Freed {_human_size(freed)}."
