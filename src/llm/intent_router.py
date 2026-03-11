"""
Intent Router for AItao.

Classifies user prompts into three intent categories without LLM overhead:
- factual   : structured queries (count, list, presence check in the index)
- summarize : full-document summarization requests (Map-Reduce — US-043)
- rag       : default semantic retrieval via RAG pipeline

Classification uses compiled regex patterns and keyword matching only.
No external call, no LLM needed.
"""

import re
from typing import Literal

# Intent type alias
IntentType = Literal["factual", "rag", "summarize"]

# ---------------------------------------------------------------------------
# Factual intent: user wants an exact count, list, or existence check
# ---------------------------------------------------------------------------
_FACTUAL_PATTERNS = [
    r"\bcombien\b",
    r"\bliste[- ]moi\b",
    r"\blist[- ]?files?\b",
    r"\bquels fichiers\b",
    r"\bquels documents?\b",
    r"\best[- ]ce que tu as\b",
    r"\bdénombre\b",
    r"\bcompte[- ]moi\b",
    r"\bhow many\b",
    r"\bcount\b",
    r"\bdo you have\b",
    r"\bquels? (sont les|sont mes)\b",
]

# ---------------------------------------------------------------------------
# Summarize intent: user wants a full-document synthesis (Map-Reduce)
# ---------------------------------------------------------------------------
_SUMMARIZE_PATTERNS = [
    r"\brésume[- ]moi\b",
    r"\bfais[- ]moi un résumé\b",
    r"\brésumé complet\b",
    r"\bsynthétise\b",
    r"\bsummariz(e|ation)\b",
    r"\bfull summary\b",
    r"\bcomplete summary\b",
    r"\bsummariz(e)? (the )?(entire|whole|complete)\b",
    r"\bprécis (complet|entier|de tout)\b",
]

_FACTUAL_RE = re.compile("|".join(_FACTUAL_PATTERNS), re.IGNORECASE)
_SUMMARIZE_RE = re.compile("|".join(_SUMMARIZE_PATTERNS), re.IGNORECASE)


class IntentRouter:
    """
    Lightweight prompt classifier using regex + keyword patterns.

    No LLM call — runs synchronously in the hot path.

    Returns:
        "factual"   — the user wants an exact count or list from the index
        "summarize" — the user wants a full-document summary (Map-Reduce)
        "rag"       — default semantic retrieval via RAG pipeline

    Usage::

        router = IntentRouter()
        intent = router.classify("combien de livres dans ~/MEGA/EBOOK/Contes ?")
        # → "factual"
    """

    def classify(self, prompt: str) -> IntentType:
        """
        Classify a user prompt into an intent category.

        Args:
            prompt: The last user message text.

        Returns:
            IntentType: "factual" | "rag" | "summarize"
        """
        if not prompt or not prompt.strip():
            return "rag"

        # Order matters: summarize before factual to avoid keyword overlap
        if _SUMMARIZE_RE.search(prompt):
            return "summarize"

        if _FACTUAL_RE.search(prompt):
            return "factual"

        return "rag"
