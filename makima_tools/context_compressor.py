"""
TOOL: Context Compressor
──────────────────────────────────────────────
Compresses long conversation history into a tight
summary so Makima never loses context but doesn't
blow up the token limit.

USAGE in ai_handler.py:
    from tools.context_compressor import ContextCompressor
    compressor = ContextCompressor()

    # Before building prompt:
    compressed = compressor.compress(conversation_history)
    # Use compressed instead of raw history in prompt
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


MAX_RAW_MESSAGES = 10        # keep last N messages raw
SUMMARY_EVERY_N = 20         # summarize every N messages above that
COMPRESSED_DIR = Path("makima_memory/compressed")


class ContextCompressor:

    def __init__(self, ai_handler=None):
        """
        ai_handler: your existing AIHandler instance.
        If None, uses extractive summarization (no API call needed).
        """
        self.ai = ai_handler
        COMPRESSED_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def compress(self, messages: List[Dict]) -> List[Dict]:
        """
        Takes full message history, returns compressed version.
        Last MAX_RAW_MESSAGES are kept verbatim.
        Older messages are summarized into a single system message.

        messages format: [{"role": "user"|"assistant", "content": "..."}]
        """
        if len(messages) <= MAX_RAW_MESSAGES:
            return messages  # Nothing to compress

        to_summarize = messages[:-MAX_RAW_MESSAGES]
        recent = messages[-MAX_RAW_MESSAGES:]

        summary = self._summarize(to_summarize)

        compressed = [
            {
                "role": "system",
                "content": f"[CONVERSATION SUMMARY — earlier context]\n{summary}"
            }
        ] + recent

        print(f"[Compressor] {len(messages)} messages → {len(compressed)} (saved {len(messages)-len(compressed)} messages)")
        return compressed

    def extract_key_facts(self, messages: List[Dict]) -> List[str]:
        """
        Pull out facts Makima should always remember:
        names, preferences, decisions made, tasks assigned.
        Returns list of fact strings.
        """
        facts = []
        for msg in messages:
            content = msg.get("content", "").lower()

            # Simple pattern extraction (no AI needed)
            if "my name is" in content or "i'm " in content or "i am " in content:
                facts.append(f"USER IDENTITY: {msg['content'][:100]}")
            if "remember that" in content or "don't forget" in content:
                facts.append(f"IMPORTANT: {msg['content'][:150]}")
            if "always " in content or "never " in content:
                facts.append(f"PREFERENCE: {msg['content'][:150]}")
            if "deadline" in content or "by " in content and "date" in content:
                facts.append(f"DEADLINE: {msg['content'][:100]}")

        return list(set(facts))  # deduplicate

    def save_session_summary(self, messages: List[Dict], session_id: str):
        """Persist a compressed summary for session resume."""
        summary = self._summarize(messages)
        facts = self.extract_key_facts(messages)

        data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "summary": summary,
            "key_facts": facts
        }

        out = COMPRESSED_DIR / f"{session_id}.json"
        out.write_text(json.dumps(data, indent=2))
        print(f"[Compressor] Session saved → {out}")
        return data

    def load_session_summary(self, session_id: str) -> Dict:
        """Load a previously compressed session."""
        path = COMPRESSED_DIR / f"{session_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}

    # ── Internals ─────────────────────────────────────────────────────────────

    def _summarize(self, messages: List[Dict]) -> str:
        """Summarize messages. Uses AI if available, else extractive fallback."""

        if self.ai:
            # AI-powered abstractive summary (best quality)
            text = "\n".join([
                f"{m['role'].upper()}: {m['content']}"
                for m in messages
            ])
            try:
                return self.ai.generate_response(
                    system_prompt=(
                        "Summarize this conversation history concisely. "
                        "Focus on: decisions made, user preferences learned, "
                        "tasks assigned, important facts mentioned. "
                        "Be brief but complete. Use bullet points."
                    ),
                    user_message=text,
                    temperature=0.2
                )
            except Exception:
                pass  # Fall through to extractive

        # Extractive fallback (no API needed)
        return self._extractive_summary(messages)

    def _extractive_summary(self, messages: List[Dict]) -> str:
        """
        No-AI fallback: extract key sentences heuristically.
        """
        important = []
        keywords = [
            "remember", "important", "always", "never", "deadline",
            "my name", "i prefer", "i like", "i don't like", "make sure",
            "note that", "decided", "confirmed", "agreed"
        ]

        for msg in messages:
            content = msg.get("content", "")
            if any(kw in content.lower() for kw in keywords):
                role = msg.get("role", "?").upper()
                important.append(f"• [{role}] {content[:200]}")

        if not important:
            # Just take first line of every few messages
            for msg in messages[::3]:
                content = msg.get("content", "")[:100]
                important.append(f"• {content}")

        return "\n".join(important[:15])  # cap at 15 bullets
