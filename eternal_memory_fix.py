"""
FIX: core/eternal_memory.py — Memory Search
─────────────────────────────────────────────
Fixes the stopword hallucination bug where "my favorite programming language"
matched "my favorite color is crimson" because of overlapping filler words.

HOW TO APPLY:
  1. Add STOPWORDS constant below your imports (outside the class)
  2. Add _extract_keywords(), _score_memory() as new methods inside EternalMemory
  3. Replace your existing search_memories() with the new one below
  4. Update build_memory_context() / wherever you build LLM prompt context
"""

# ── STEP 1: Add this below your imports, outside the class ───────────────────

STOPWORDS = {
    # Articles / determiners
    "a","an","the","this","that","these","those","my","your",
    "his","her","its","our","their","some","any","all","each",
    # Auxiliary verbs
    "is","are","was","were","be","been","being","am",
    "do","does","did","have","has","had","will","would",
    "can","could","should","shall","may","might","must",
    # Question words (alone they carry no subject meaning)
    "what","who","where","when","how","why",
    # Prepositions / conjunctions
    "in","on","at","to","for","of","with","by","from",
    "and","or","but","so","yet","if","then","than","into",
    # Common filler
    "i","me","we","you","it","just","also","very","really",
    "about","know","tell","think","get","got","let",
    # Preference connector words — these blur context across all preference notes
    "favorite","favourite","preferred","prefer","default",
    "usual","best","love","enjoy","use","used","using","like",
}


# ── STEP 2: Add these 2 methods inside your EternalMemory class ──────────────

def _extract_keywords(self, text: str) -> set:
    """Strip stopwords and noise — return only meaningful words."""
    import re
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _score_memory(self, query_keywords: set, note: dict) -> float:
    """
    Score a note against query keywords.
    Uses Jaccard similarity + coverage + stem matching + phrase bonus.
    Returns 0.0–1.0. Returns 0.0 if no meaningful overlap.
    """
    import re
    note_text = note.get("text", "").lower()
    note_keywords = self._extract_keywords(note_text)

    if not query_keywords or not note_keywords:
        return 0.0

    # Exact keyword overlap
    overlap = query_keywords & note_keywords

    # Stem overlap — "editor" matches "editors", "code" matches "coding"
    for qw in query_keywords:
        for nw in note_keywords:
            if len(qw) >= 4 and len(nw) >= 4:
                if qw.startswith(nw[:4]) or nw.startswith(qw[:4]):
                    overlap.add(qw)

    if not overlap:
        return 0.0   # Zero overlap on meaningful words → not a match

    # Jaccard + coverage blend
    union     = query_keywords | note_keywords
    jaccard   = len(overlap) / len(union)
    coverage  = len(overlap) / len(query_keywords)
    score     = (jaccard * 0.5 + coverage * 0.5) * 0.7

    # Phrase bonus: 2+ consecutive keywords appearing together in note
    kw_list = list(query_keywords)
    for i in range(len(kw_list) - 1):
        phrase = kw_list[i] + " " + kw_list[i + 1]
        if phrase in note_text:
            score += 0.25
            break

    # Tag bonus
    note_tags = [t.lower() for t in note.get("tags", [])]
    if any(kw in note_tags for kw in query_keywords):
        score += 0.15

    return min(score, 1.0)


# ── STEP 3: Replace your existing search_memories() with this ────────────────

def search_memories(self, query: str, top_k: int = 3) -> list:
    """
    Search notes by meaningful keyword overlap only.
    Ignores stopwords so generic words like 'my', 'favorite', 'is'
    never cause wrong notes to match.
    """
    if not query or not query.strip():
        return []

    notes = self._load_notes()   # your existing method
    if not notes:
        return []

    query_keywords = self._extract_keywords(query)
    if not query_keywords:
        return []   # query is all stopwords — don't match everything

    scored = []
    for note in notes:
        score = self._score_memory(query_keywords, note)
        if score > 0:
            scored.append((score, note))

    scored.sort(key=lambda x: x[0], reverse=True)

    MIN_SCORE = 0.15   # below this = not confident enough to use
    return [note for score, note in scored if score >= MIN_SCORE][:top_k]


# ── STEP 4: Update your LLM prompt builder ───────────────────────────────────
# Find wherever you inject memory into the AI prompt and change it to this:

def build_memory_context(self, query: str) -> str:
    """
    Returns memory context string for the LLM prompt.
    Returns empty string if nothing relevant — prevents hallucination.
    """
    notes = self.search_memories(query, top_k=3)
    if not notes:
        return ""   # ← key: no bad context = no hallucination

    lines = ["[Relevant memories:]"]
    for note in notes:
        text = note.get("text", "").strip()
        if text:
            lines.append(f"- {text}")
    lines.append("[Only use above if directly relevant to the question.]")
    return "\n".join(lines)


# In ai_handler.py, change your prompt builder from:
#
#   memories = self.memory.search_memories(user_input)
#   memory_text = "\n".join(m["text"] for m in memories)   # ← BAD: injects all matches
#
# To:
#
#   memory_text = self.memory.build_memory_context(user_input)  # ← GOOD: filtered


# ── QUICK VERIFICATION (run: python eternal_memory_fix.py) ───────────────────

if __name__ == "__main__":
    import re

    def kw(text):
        words = re.sub(r"[^\w\s]"," ",text.lower()).split()
        return {w for w in words if w not in STOPWORDS and len(w) > 2}

    def score(q_kw, note_text):
        n_kw = kw(note_text)
        overlap = q_kw & n_kw
        for qw in q_kw:
            for nw in n_kw:
                if len(qw)>=4 and len(nw)>=4 and (qw.startswith(nw[:4]) or nw.startswith(qw[:4])):
                    overlap.add(qw)
        if not overlap: return 0.0
        j = len(overlap)/(len(q_kw|n_kw))
        c = len(overlap)/len(q_kw)
        return (j*0.5+c*0.5)*0.7

    tests = [
        ("What is my favorite programming language?",
         "favorite programming language is Python",
         "favorite color is crimson"),
        ("What music do I listen to?",
         "user likes lo-fi music while coding",
         "favorite color is crimson"),
        ("What is my favorite color?",
         "favorite color is crimson",
         "favorite programming language is Python"),
        ("What code editor do I use?",
         "user prefers dark mode in all editors",
         "favorite color is crimson"),
    ]

    print("Memory fix verification")
    print("="*55)
    passed = 0
    for query, right, wrong in tests:
        q = kw(query)
        sr, sw = score(q, right), score(q, wrong)
        ok = sr >= sw
        if ok: passed += 1
        print(f"{'✅' if ok else '❌'}  {query}")
        print(f"   Right ({sr:.2f}): {right[:45]}")
        print(f"   Wrong ({sw:.2f}): {wrong[:45]}")
        print()

    print(f"Result: {passed}/{len(tests)} passed {'✅' if passed==len(tests) else '❌'}")
