"""
Map-Reduce Summarizer for AItao.

Handles full-document summarization when the user asks for a complete
synthesis of a specific document.

Pipeline:
1. Find the target document by title/path in Meilisearch
2. Retrieve all chunks from ChunkStore (LanceDB) using doc_id
3. Map  : summarize each group of GROUP_SIZE chunks independently
4. Reduce: produce a final synthesis from the partial summaries

The mapping step yields intermediate summaries progressively.
Each summary is yielded as a plain string so callers can stream it.

Safety cap: MAX_CHUNKS = 100 (beyond that, representative sampling).
"""

import math
import os
import re
from typing import Any, Generator, List, Optional

from src.core.logger import get_logger

logger = get_logger("llm.summarizer")

_GROUP_SIZE = 5        # Chunks per map group
_MAX_CHUNKS = 100      # Safety cap before representative sampling


def _extract_doc_name_from_prompt(prompt: str) -> Optional[str]:
    """
    Extract a document name/title fragment from a summarize prompt.

    Matches patterns such as:
      "résume-moi Ergonomie des interfaces - Dunod.pdf"
      "summarize the file report_2025.docx"

    Args:
        prompt: Raw user message text.

    Returns:
        Extracted file/title fragment, or None.
    """
    # Pattern 1: after a quote or guillemet
    m = re.search(r'["\u00ab\u2018\u201c]([^"\u00bb\u2019\u201d]+)', prompt)
    if m:
        return m.group(1).strip()

    # Pattern 2: a filename token (contains "." with known extensions)
    m = re.search(
        r"([\w\s\-\u00c0-\u024f]+\.(?:pdf|docx?|txt|md|epub|odt|rtf))",
        prompt,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    # Pattern 3: after "résume-moi", "summarize", "résumé de", etc.
    m = re.search(
        r"(?:résume[- ]moi|summarize|résumé de|synthèse de|synthétise)\s+(.+?)(?:\s*\?|$)",
        prompt,
        re.IGNORECASE | re.UNICODE,
    )
    if m:
        return m.group(1).strip()

    return None


class MapReduceSummarizer:
    """
    Full-document summarizer using a Map-Reduce pipeline.

    Uses ChunkStore and MeilisearchClient to locate and retrieve
    all chunks of a document, then runs an iterative LLM summarization.

    Usage::

        summarizer = MapReduceSummarizer()
        for part in summarizer.summarize_prompt(prompt, ollama_call_fn):
            print(part)

    Args:
        config: Optional ConfigManager instance (lazy-loaded if None).
    """

    def __init__(self, config: Optional[Any] = None):
        self._config = config
        self._chunk_store: Optional[Any] = None
        self._meilisearch: Optional[Any] = None

    @property
    def chunk_store(self):
        """Lazy-load ChunkStore."""
        if self._chunk_store is None:
            from src.core.config import get_config
            from src.indexation.chunk_store import ChunkStore
            cfg = self._config or get_config()
            db_path = cfg.get("storage", {}).get("lancedb_path") or None
            self._chunk_store = ChunkStore(db_path=db_path)
        return self._chunk_store

    @property
    def meilisearch(self):
        """Lazy-load MeilisearchClient."""
        if self._meilisearch is None:
            from src.core.config import get_config
            from src.search.meilisearch_client import MeilisearchClient
            cfg = self._config or get_config()
            self._meilisearch = MeilisearchClient(cfg, logger)
        return self._meilisearch

    def _find_doc_id(self, doc_name: str) -> Optional[str]:
        """
        Search Meilisearch for a document matching doc_name and return its ID (SHA256).

        Args:
            doc_name: Title or filename fragment to search.

        Returns:
            doc_id string, or None if not found.
        """
        results = self.meilisearch.search(query=doc_name, limit=5)
        if not results:
            return None
        # Prefer exact filename match
        for r in results:
            if doc_name.lower() in (r.get("title") or "").lower():
                return r.get("id") or r.get("doc_id")
            if doc_name.lower() in (r.get("path") or "").lower():
                return r.get("id") or r.get("doc_id")
        # Fallback: first result
        return results[0].get("id") or results[0].get("doc_id")

    def _representative_sample(self, chunks: list, n: int = _MAX_CHUNKS) -> list:
        """
        Return n evenly-spaced chunks from a list (preserves document order).

        Args:
            chunks: Ordered chunk list.
            n: Maximum chunks to keep.

        Returns:
            Sub-sampled list.
        """
        if len(chunks) <= n:
            return chunks
        step = len(chunks) / n
        return [chunks[math.floor(i * step)] for i in range(n)]

    def summarize_prompt(
        self,
        prompt: str,
        llm_fn,
        group_size: int = _GROUP_SIZE,
    ) -> Generator[str, None, None]:
        """
        Full summarization pipeline (Map-Reduce).

        Yields intermediate status strings and partial summaries so the
        caller can stream them progressively to the user.

        Args:
            prompt: The user's raw message text.
            llm_fn: Callable(prompt: str) -> str — synchronous LLM call
                    (no streaming; used internally for map/reduce passes).
            group_size: Number of chunks per map group.

        Yields:
            Status strings (e.g., "Analysing part 1/12...") and partial
            summaries, then the final synthesis.
        """
        doc_name = _extract_doc_name_from_prompt(prompt)
        if not doc_name:
            yield (
                "I could not identify the document name in your request. "
                "Please specify the exact title or filename."
            )
            return

        yield f"Searching for document: **{doc_name}** …"

        doc_id = self._find_doc_id(doc_name)
        if not doc_id:
            yield (
                f"No document matching **{doc_name}** was found in the index. "
                "Make sure the document has been indexed."
            )
            return

        chunks = self.chunk_store.get_chunks_by_doc_id(doc_id)
        if not chunks:
            yield (
                f"Document found but no text chunks available. "
                "The document may not have been chunked yet."
            )
            return

        total_chunks = len(chunks)
        yield f"Found {total_chunks} chunk(s) for **{doc_name}**. Starting summarization…"

        # Safety cap: sample representative chunks
        if total_chunks > _MAX_CHUNKS:
            chunks = self._representative_sample(chunks, _MAX_CHUNKS)
            yield (
                f"(Document is long — using {len(chunks)} representative "
                f"chunks out of {total_chunks} to stay within limits.)"
            )

        # ---- Map phase ----
        groups = [
            chunks[i : i + group_size]
            for i in range(0, len(chunks), group_size)
        ]
        n_groups = len(groups)
        partial_summaries: List[str] = []

        for idx, group in enumerate(groups, start=1):
            yield f"Analysing part {idx}/{n_groups}…"
            combined = "\n\n".join(c.content for c in group)
            map_prompt = (
                f"Summarize the following text excerpt (part {idx} of {n_groups} "
                f"from '{doc_name}'). Be concise (3-5 sentences), preserve key facts.\n\n"
                f"{combined}"
            )
            try:
                summary = llm_fn(map_prompt)
                partial_summaries.append(f"**Part {idx}:** {summary}")
                yield partial_summaries[-1]
            except Exception as exc:
                logger.warning(f"Map pass failed for group {idx}: {exc}")
                partial_summaries.append(f"**Part {idx}:** (summarization failed)")

        # ---- Reduce phase ----
        yield "\n---\n**Generating final synthesis…**"
        combined_summaries = "\n\n".join(partial_summaries)
        reduce_prompt = (
            f"Based on the following partial summaries of '{doc_name}', "
            f"write a complete and coherent final summary (1-2 paragraphs). "
            f"Highlight the main themes and key takeaways.\n\n"
            f"{combined_summaries}"
        )
        try:
            final = llm_fn(reduce_prompt)
            yield f"\n---\n**Final summary of '{doc_name}':**\n\n{final}"
        except Exception as exc:
            logger.error(f"Reduce phase failed: {exc}")
            yield (
                "\n---\n**Final summary could not be generated.** "
                "See partial summaries above."
            )
