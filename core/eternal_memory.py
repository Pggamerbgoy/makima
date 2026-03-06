"""
core/eternal_memory.py
Permanent long-term memory with TF-IDF semantic search.
Stores every conversation across sessions and retrieves relevant context.
"""

import os
import json
import math
import logging
import re
from datetime import datetime
from collections import defaultdict
import threading
from typing import Optional

logger = logging.getLogger("Makima.Memory")

STOPWORDS = {
    "a","an","the","this","that","these","those","my","your",
    "his","her","its","our","their","some","any","all","each",
    "is","are","was","were","be","been","being","am",
    "do","does","did","have","has","had","will","would",
    "can","could","should","shall","may","might","must",
    "what","who","where","when","how","why",
    "in","on","at","to","for","of","with","by","from",
    "and","or","but","so","yet","if","then","than","into",
    "i","me","we","you","it","just","also","very","really",
    "about","know","tell","think","get","got","let",
    "favorite","favourite","preferred","prefer","default",
    "usual","best","love","enjoy","use","used","using","like",
}

MEMORY_DIR = "makima_memory"
CONVERSATIONS_FILE = os.path.join(MEMORY_DIR, "conversations.jsonl")
NOTES_FILE = os.path.join(MEMORY_DIR, "notes.json")


class TFIDFSearch:
    """Lightweight TF-IDF implementation — no sklearn required."""

    def __init__(self):
        self.documents: list[str] = []
        self.tf_idf_matrix: list[dict] = []
        self.idf: dict[str, float] = {}

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'\b[a-z]{2,}\b', text.lower())

    def _tf(self, tokens: list[str]) -> dict[str, float]:
        counts: dict[str, int] = defaultdict(int)
        for t in tokens:
            counts[t] += 1
        total = len(tokens) or 1
        return {t: c / total for t, c in counts.items()}

    def fit(self, documents: list[str]):
        self.documents = documents
        N = len(documents)
        if N == 0:
            return

        # Count document frequencies
        df: dict[str, int] = defaultdict(int)
        tokenized_docs = []
        for doc in documents:
            tokens = set(self._tokenize(doc))
            tokenized_docs.append(tokens)
            for t in tokens:
                df[t] += 1

        # Compute IDF
        self.idf = {t: math.log((N + 1) / (f + 1)) + 1 for t, f in df.items()}

        # Compute TF-IDF vectors
        self.tf_idf_matrix = []
        for doc in documents:
            tokens = self._tokenize(doc)
            tf = self._tf(tokens)
            vec = {t: tf[t] * self.idf.get(t, 1) for t in tf}
            self.tf_idf_matrix.append(vec)

    def _cosine(self, vec_a: dict, vec_b: dict) -> float:
        common = set(vec_a) & set(vec_b)
        if not common:
            return 0.0
        dot = sum(vec_a[k] * vec_b[k] for k in common)
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def search(self, query: str, top_k: int = 3) -> list[tuple[float, str]]:
        if not self.documents:
            return []
        tokens = self._tokenize(query)
        tf = self._tf(tokens)
        query_vec = {t: tf[t] * self.idf.get(t, 1) for t in tf}

        scores = [
            (self._cosine(query_vec, doc_vec), self.documents[i])
            for i, doc_vec in enumerate(self.tf_idf_matrix)
        ]
        scores.sort(key=lambda x: x[0], reverse=True)
        return [(s, d) for s, d in scores if s > 0.01][:top_k]


class EternalMemory:
    """Persistent long-term memory across sessions."""

    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.notes: dict[str, str] = self._load_notes()
        self.search_engine = TFIDFSearch()
        self._corpus: list[str] = []
        self._lock = threading.Lock()
        self._rebuild_index()
        logger.info(f"🧠 Memory loaded. {len(self._corpus)} conversation entries indexed.")

    # ─── Persistence ──────────────────────────────────────────────────────────

    def _load_notes(self) -> dict:
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_notes(self):
        with self._lock:
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=2)

    def _rebuild_index(self):
        """Load all conversations from disk and rebuild TF-IDF index."""
        self._corpus = []
        if not os.path.exists(CONVERSATIONS_FILE):
            return
        try:
            with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        self._corpus.append(entry.get("content", ""))
        except Exception as e:
            logger.warning(f"Memory load error: {e}")

        self.search_engine.fit(self._corpus)

    # ─── Conversation Logging ─────────────────────────────────────────────────

    def save_conversation(self, role: str, content: str):
        """Append a conversation turn to the log."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
        }
        with self._lock:
            try:
                with open(CONVERSATIONS_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                self._corpus.append(content)
                # Re-index periodically — every 50 writes to avoid O(n²) on rapid bursts,
                # and immediately on the first few entries so a fresh session is searchable.
                if len(self._corpus) <= 5 or len(self._corpus) % 50 == 0:
                    self.search_engine.fit(self._corpus)
            except Exception as e:
                logger.warning(f"Memory write error: {e}")

    # ─── Notes / Explicit Memories ────────────────────────────────────────────

    def remember(self, key: str, value: str):
        """Alias for save_note to maintain compatibility."""
        self.save_note(value, key=key)

    def save_note(self, content: str, key: str = None):
        """Auto-generate a key from content if not provided."""
        if not key:
            words = content.split()
            key = " ".join(words[:3])
        # Normalize key to lowercase so recall_note's .lower() lookup always matches
        self.notes[key.lower()] = content
        self._save_notes()

    def recall_note(self, key: str) -> Optional[str]:
        """Enhanced recall with exact match priority and partial fallback."""
        key_lower = key.lower()
        if key_lower in self.notes:
            return self.notes[key_lower]
        
        for k, v in self.notes.items():
            if key_lower in k.lower() or k.lower() in key_lower:
                return v
        return None

    # ─── Semantic Search ──────────────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> set:
        """Strip stopwords and noise — return only meaningful words."""
        words = re.sub(r"[^\w\s]", " ", text.lower()).split()
        return {w for w in words if w not in STOPWORDS and len(w) > 2}

    def _score_memory(self, query_keywords: set, text: str) -> float:
        """Score a note against query keywords."""
        note_text = text.lower()
        note_keywords = self._extract_keywords(note_text)
        if not query_keywords or not note_keywords: return 0.0

        overlap = query_keywords & note_keywords
        # Add fuzzy overlap
        for qw in query_keywords:
            for nw in note_keywords:
                if len(qw) >= 4 and len(nw) >= 4:
                    if qw.startswith(nw[:4]) or nw.startswith(qw[:4]):
                        overlap.add(qw)

        if not overlap: return 0.0
        union = query_keywords | note_keywords
        jaccard = len(overlap) / len(union)
        coverage = len(overlap) / len(query_keywords)
        score = (jaccard * 0.5 + coverage * 0.5) * 0.7
        return min(score, 1.0)

    def search_memories(self, query: str, top_k: int = 3) -> list:
        if not query or not query.strip(): return []
        query_keywords = self._extract_keywords(query)
        if not query_keywords: return []

        scored = []
        for key, value in self.notes.items():
            note_text = f"{key}: {value}"
            score = self._score_memory(query_keywords, note_text)
            if score > 0: scored.append((score, note_text))

        scored.sort(key=lambda x: x[0], reverse=True)
        memories = [note_text for _, note_text in scored if _ >= 0.15][:top_k]
        
        # Add semantic conversation history fallback
        if len(memories) < top_k:
            results = self.search_engine.search(query, top_k=top_k)
            memories.extend([doc for _, doc in results])
            
        return list(dict.fromkeys(memories))[:top_k]

    def build_memory_context(self, query: str) -> str:
        notes = self.search_memories(query, top_k=3)
        if not notes: return ""
        lines = ["[Relevant memories:]"]
        for note in notes:
            if note.strip(): lines.append(f"- {note.strip()}")
        lines.append("[Only use above if directly relevant to the question.]")
        return "\n".join(lines)

    def search(self, query: str) -> Optional[str]:
        """Generic search for backward compatibility."""
        results = self.search_memories(query, top_k=1)
        return results[0] if results else None

    # ─── Stats ────────────────────────────────────────────────────────────────

    def format_stats(self) -> str:
        s = self.get_stats()
        return (
            f"I have {s['total_entries']} conversation memories "
            f"and {s['notes_count']} saved notes."
        )

    def get_stats(self) -> dict:
        return {
            "total_entries": len(self._corpus),
            "notes_count": len(self.notes),
            "memory_file": CONVERSATIONS_FILE,
        }
