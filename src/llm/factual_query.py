"""
Factual Query Handler for AItao.

Handles structured factual queries about indexed documents:
- File count in a directory (by path prefix)
- File listing by path prefix

Queries Meilisearch directly and returns a formatted context string
ready to be injected into the system message of the LLM request.
Bypasses the full RAG pipeline to provide exact, deterministic answers.
"""

import os
import re
from typing import Any, Dict, List, Optional

from src.core.logger import get_logger

logger = get_logger("llm.factual_query")

# Regex to extract a filesystem path from a user prompt.
# Matches:  ~/...  /...  C:\...  D:/...
_PATH_RE = re.compile(
    r"(~[/\\][^\s,;?!。]+|[A-Za-z]:[/\\][^\s,;?!。]+|/(?:[^\s,;?!。]+))",
    re.UNICODE,
)


def extract_path_from_prompt(prompt: str) -> Optional[str]:
    """
    Extract the first filesystem path fragment from a prompt string.

    Args:
        prompt: User message text.

    Returns:
        Expanded absolute path, or None if no path found.
    """
    match = _PATH_RE.search(prompt)
    if match:
        raw = match.group(1).rstrip("/\\.,;:?!")
        return os.path.expanduser(raw)
    return None


class FactualQueryHandler:
    """
    Answers factual file-system questions by querying Meilisearch directly.

    Methods:
        count_files(path_filter)   — count indexed documents under a path prefix
        list_files(path_filter)    — list {title, path} dicts under a path prefix
        handle(prompt)             — classify + query + format context string

    Usage::

        handler = FactualQueryHandler()
        context = handler.handle("combien de livres dans ~/MEGA/EBOOK/Contes ?")
        # → "[AItao system: 12 indexed document(s) found under /Users/.../MEGA/EBOOK/Contes]"
    """

    def __init__(self, config: Optional[Any] = None):
        self._meilisearch: Optional[Any] = None
        self._config = config

    @property
    def meilisearch(self):
        """Lazy-load MeilisearchClient."""
        if self._meilisearch is None:
            from src.core.config import get_config
            from src.search.meilisearch_client import MeilisearchClient
            cfg = self._config or get_config()
            self._meilisearch = MeilisearchClient(cfg, logger)
        return self._meilisearch

    def count_files(self, path_filter: str) -> int:
        """
        Return exact document count for a directory path prefix.

        Args:
            path_filter: Directory path (expanded, absolute).

        Returns:
            Number of indexed documents whose path starts with path_filter.
        """
        all_paths = self.meilisearch.get_all_document_paths()
        return sum(1 for p in all_paths if p.startswith(path_filter))

    def list_files(
        self,
        path_filter: str,
        limit: int = 20,
    ) -> List[Dict[str, str]]:
        """
        Return a list of {title, path} for documents under a path prefix.

        Uses Meilisearch full-text search on the directory name, then filters
        results in Python to exact prefix matches.

        Args:
            path_filter: Directory path (expanded, absolute).
            limit: Maximum number of results to return.

        Returns:
            List of dicts with "title" and "path" keys.
        """
        fragment = os.path.basename(path_filter.rstrip("/\\")) or path_filter
        try:
            results = self.meilisearch.search(query=fragment, limit=200)
        except Exception as exc:
            logger.warning(f"Meilisearch search failed in factual handler: {exc}")
            results = []

        matches = [
            {
                "path": r.get("path", ""),
                "title": r.get("title") or os.path.basename(r.get("path", "")),
            }
            for r in results
            if r.get("path", "").startswith(path_filter)
        ]
        return matches[:limit]

    def handle(self, prompt: str) -> str:
        """
        Build a structured context string from a factual user prompt.

        Extracts the path from the prompt, queries Meilisearch, and returns
        a formatted context block ready to be injected into the LLM system message.

        Args:
            prompt: Raw user message text.

        Returns:
            Formatted context string, or empty string if no path detected.
        """
        path = extract_path_from_prompt(prompt)
        if not path:
            logger.debug("FactualQueryHandler: no path found in prompt, skipping")
            return ""

        prompt_lower = prompt.lower()
        is_list = any(
            kw in prompt_lower
            for kw in (
                "liste", "list", "quels fichiers", "quels documents",
                "montre-moi", "show me", "donne-moi",
            )
        )

        if is_list:
            files = self.list_files(path)
            if not files:
                return f"[AItao system: no indexed documents found under {path}]"
            lines = "\n".join(
                f"  - {f['title']} ({f['path']})" for f in files
            )
            return (
                f"[AItao system: {len(files)} document(s) found under {path}]\n{lines}"
            )

        count = self.count_files(path)
        if count == 0:
            return f"[AItao system: no indexed documents found under {path}]"
        return f"[AItao system: {count} indexed document(s) found under {path}]"
