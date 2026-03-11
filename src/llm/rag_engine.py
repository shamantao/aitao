"""
RAG (Retrieval-Augmented Generation) Engine for AItao.

This module provides the RAGEngine class that enriches user prompts
with relevant context from indexed documents before sending to LLM.

Workflow:
1. User prompt received
2. Search indexed chunks (fine-grained) or documents (fallback)
3. Extract relevant context snippets
4. Build enriched prompt with context
5. Return enriched prompt + context for transparency

The RAG approach allows the LLM to answer questions about local documents
it has never seen during training. Chunk-based retrieval provides more
precise context than full document retrieval.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import time

from src.core.config import ConfigManager
from src.core.license import LicenseManager
from src.core.logger import StructuredLogger


@dataclass
class ContextDocument:
    """
    A document retrieved as context for RAG.
    
    Attributes:
        id: Document ID (SHA256 hash)
        path: Absolute file path
        title: Document title or filename
        content: Relevant text excerpt
        score: Relevance score (0-1)
        category: Document category
        language: Detected language
    """
    id: str
    path: str
    title: str
    content: str
    score: float
    category: Optional[str] = None
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextChunk:
    """
    A chunk retrieved as context for RAG.
    
    Chunks are fine-grained text segments (typically 512 tokens)
    that provide more precise context than full documents.
    
    Attributes:
        chunk_id: Unique chunk identifier
        doc_id: Parent document ID
        path: Source file path
        title: Document title
        content: Chunk text content
        chunk_index: Position within document (0-indexed)
        total_chunks: Total chunks in source document
        score: Relevance score (0-1)
        metadata: Additional metadata
    """
    chunk_id: str
    doc_id: str
    path: str
    title: str
    content: str
    chunk_index: int
    total_chunks: int
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGResult:
    """
    Result from RAG context enrichment.
    
    Attributes:
        original_prompt: The user's original prompt
        enriched_prompt: Prompt with context prepended
        context_docs: List of documents used as context (fallback mode)
        context_chunks: List of chunks used as context (preferred mode)
        total_context_tokens: Estimated token count of context
        search_time_ms: Time spent searching for context
        mode: Retrieval mode used ('chunks' or 'documents')
    """
    original_prompt: str
    enriched_prompt: str
    context_docs: List[ContextDocument]
    context_chunks: List[ContextChunk] = field(default_factory=list)
    total_context_tokens: int = 0
    search_time_ms: float = 0.0
    mode: str = "documents"


class RAGEngine:
    """
    Retrieval-Augmented Generation Engine.
    
    Enriches user prompts with relevant context from indexed documents
    using hybrid search (semantic + full-text). The enriched prompt
    allows LLMs to answer questions about local documents.
    
    Example:
        >>> rag = RAGEngine(config, logger)
        >>> result = rag.enrich_prompt("Comment fonctionne le module OCR?")
        >>> print(result.enriched_prompt)
        # Includes context from indexed Python files and docs
        >>> print(result.context_docs)
        # Shows which documents were used
    
    Configuration (config.toml):
        rag:
            max_context_docs: 5      # Max documents to include
            max_context_chunks: 5    # Max chunks to include (preferred)
            context_max_tokens: 2000 # Max tokens for context section
            min_relevance_score: 0.3 # Min score to include document/chunk
            include_metadata: true   # Include file path, category in context
            use_chunks: true         # Prefer chunk-based retrieval (US-023)
    """
    
    # Default configuration values
    DEFAULT_MAX_CONTEXT_DOCS = 5
    DEFAULT_MAX_CONTEXT_CHUNKS = 5
    DEFAULT_CONTEXT_MAX_TOKENS = 2000
    DEFAULT_MIN_RELEVANCE_SCORE = 0.3
    DEFAULT_INCLUDE_METADATA = True
    DEFAULT_USE_CHUNKS = True
    
    # Approximate chars per token (for estimation)
    CHARS_PER_TOKEN = 4
    
    def __init__(self, config: ConfigManager, logger: StructuredLogger):
        """
        Initialize RAGEngine.
        
        Args:
            config: ConfigManager instance for reading config.toml
            logger: StructuredLogger instance for logging
        """
        # Premium feature — blocked in Core edition
        LicenseManager().require_premium("rag_chat")

        self.config = config
        self.logger = logger
        
        # Load RAG configuration
        rag_config = config.get_section("rag") or {}
        self.max_context_docs = rag_config.get(
            "max_context_docs", self.DEFAULT_MAX_CONTEXT_DOCS
        )
        self.max_context_chunks = rag_config.get(
            "max_context_chunks", self.DEFAULT_MAX_CONTEXT_CHUNKS
        )
        self.context_max_tokens = rag_config.get(
            "context_max_tokens", self.DEFAULT_CONTEXT_MAX_TOKENS
        )
        self.min_relevance_score = rag_config.get(
            "min_relevance_score", self.DEFAULT_MIN_RELEVANCE_SCORE
        )
        self.include_metadata = rag_config.get(
            "include_metadata", self.DEFAULT_INCLUDE_METADATA
        )
        self.use_chunks = rag_config.get(
            "use_chunks", self.DEFAULT_USE_CHUNKS
        )
        
        # Lazy-loaded search engine
        self._search_engine = None
        
        self.logger.info(
            "RAGEngine initialized",
            metadata={
                "max_context_docs": self.max_context_docs,
                "max_context_chunks": self.max_context_chunks,
                "context_max_tokens": self.context_max_tokens,
                "min_relevance_score": self.min_relevance_score,
                "use_chunks": self.use_chunks,
            }
        )
    
    @property
    def search_engine(self):
        """Lazy-load HybridSearchEngine."""
        if self._search_engine is None:
            try:
                from src.search.hybrid_engine import HybridSearchEngine
                self._search_engine = HybridSearchEngine()
            except Exception as e:
                self.logger.error(
                    "Failed to initialize HybridSearchEngine",
                    metadata={"error": str(e)}
                )
                raise
        return self._search_engine
    
    def search_context(
        self,
        query: str,
        max_docs: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ContextDocument]:
        """
        Search for relevant documents to use as context.
        
        Args:
            query: The user's query/prompt
            max_docs: Override max documents to retrieve
            filters: Optional search filters (path, category, language, etc.)
        
        Returns:
            List of ContextDocument objects sorted by relevance
        """
        max_docs = max_docs or self.max_context_docs
        
        self.logger.debug(
            "Searching for context",
            metadata={"query": query[:100], "max_docs": max_docs}
        )
        
        try:
            # Import SearchFilter for type construction
            from src.search.hybrid_engine import SearchFilter
            
            # Build search filter
            search_filter = None
            if filters:
                search_filter = SearchFilter(
                    path_contains=filters.get("path_contains"),
                    category=filters.get("category"),
                    language=filters.get("language"),
                )
            
            # Execute hybrid search
            response = self.search_engine.search_sync(
                query=query,
                limit=max_docs * 2,  # Get more to filter by score
                filters=search_filter,
            )
            
            # Convert to ContextDocument and filter by score
            context_docs = []
            for result in response.results:
                if result.score >= self.min_relevance_score:
                    context_docs.append(ContextDocument(
                        id=result.id,
                        path=result.path,
                        title=result.title,
                        content=result.content,
                        score=result.score,
                        category=result.category,
                        language=result.language,
                        metadata=result.metadata,
                    ))
            
            # Limit to max_docs
            context_docs = context_docs[:max_docs]
            
            self.logger.info(
                "Context search completed",
                metadata={
                    "query": query[:50],
                    "docs_found": len(context_docs),
                    "search_time_ms": response.search_time_ms,
                }
            )
            
            return context_docs
            
        except Exception as e:
            self.logger.error(
                "Context search failed",
                metadata={"error": str(e), "query": query[:50]}
            )
            # Return empty list on error - don't block the prompt
            return []
    
    def search_chunks_context(
        self,
        query: str,
        max_chunks: Optional[int] = None,
    ) -> List[ContextChunk]:
        """
        Search for relevant chunks to use as context (US-023).
        
        Chunks provide fine-grained context (~512 tokens each) which is
        more precise than full documents. This is the preferred method
        for RAG when chunks are available.
        
        Args:
            query: The user's query/prompt
            max_chunks: Override max chunks to retrieve
        
        Returns:
            List of ContextChunk objects sorted by relevance
        """
        max_chunks = max_chunks or self.max_context_chunks
        
        self.logger.debug(
            "Searching for chunk context",
            metadata={"query": query[:100], "max_chunks": max_chunks}
        )
        
        try:
            # Execute chunk search
            response = self.search_engine.search_chunks(
                query=query,
                limit=max_chunks,
                min_score=self.min_relevance_score,
            )
            
            # Convert to ContextChunk
            context_chunks = []
            for chunk in response.chunks:
                context_chunks.append(ContextChunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    path=chunk.path,
                    title=chunk.title,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    total_chunks=chunk.total_chunks,
                    score=chunk.score,
                    metadata=chunk.metadata,
                ))
            
            self.logger.info(
                "Chunk context search completed",
                metadata={
                    "query": query[:50],
                    "chunks_found": len(context_chunks),
                    "unique_docs": response.unique_docs,
                    "search_time_ms": response.search_time_ms,
                }
            )
            
            return context_chunks
            
        except Exception as e:
            self.logger.warning(
                "Chunk search failed, falling back to document search",
                metadata={"error": str(e), "query": query[:50]}
            )
            # Return empty - caller should fallback to document search
            return []
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text length."""
        return len(text) // self.CHARS_PER_TOKEN
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximately max_tokens."""
        max_chars = max_tokens * self.CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."
    
    def _format_context_document(self, doc: ContextDocument, index: int) -> str:
        """
        Format a single context document for inclusion in prompt.
        
        Args:
            doc: The context document
            index: 1-based index for reference
        
        Returns:
            Formatted string representation
        """
        lines = [f"[{index}] {doc.title}"]
        
        if self.include_metadata:
            if doc.path:
                lines.append(f"    Path: {doc.path}")
            if doc.category:
                lines.append(f"    Category: {doc.category}")
            if doc.score:
                lines.append(f"    Relevance: {doc.score:.0%}")
        
        # Add content excerpt
        content_preview = doc.content[:500] if doc.content else ""
        if content_preview:
            lines.append(f"    Content: {content_preview}")
        
        return "\n".join(lines)
    
    def _format_context_chunk(self, chunk: ContextChunk, index: int) -> str:
        """
        Format a single context chunk for inclusion in prompt.
        
        Args:
            chunk: The context chunk
            index: 1-based index for reference
        
        Returns:
            Formatted string representation
        """
        # Show chunk position within document
        position = f"[Part {chunk.chunk_index + 1}/{chunk.total_chunks}]"
        lines = [f"[{index}] {chunk.title} {position}"]
        
        if self.include_metadata:
            if chunk.path:
                lines.append(f"    Source: {chunk.path}")
            if chunk.score:
                lines.append(f"    Relevance: {chunk.score:.0%}")
        
        # Add full chunk content (chunks are already sized appropriately)
        if chunk.content:
            lines.append(f"    Content: {chunk.content}")
        
        return "\n".join(lines)
    
    def _build_chunks_context_section(
        self,
        context_chunks: List[ContextChunk],
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Build the context section from chunks.
        
        Args:
            context_chunks: Chunks to include as context
            max_tokens: Max tokens for context section
        
        Returns:
            Formatted context section string
        """
        if not context_chunks:
            return ""
        
        max_tokens = max_tokens or self.context_max_tokens
        
        # Count unique documents
        unique_docs = len(set(c.doc_id for c in context_chunks))
        
        lines = [
            "=" * 60,
            "CONTEXT FROM YOUR DOCUMENTS",
            f"Found {len(context_chunks)} relevant passages from {unique_docs} document(s):",
            "=" * 60,
            "",
        ]
        
        tokens_used = self._estimate_tokens("\n".join(lines))
        chunks_included = 0
        
        for i, chunk in enumerate(context_chunks, 1):
            chunk_text = self._format_context_chunk(chunk, i)
            chunk_tokens = self._estimate_tokens(chunk_text)
            
            if tokens_used + chunk_tokens > max_tokens:
                # Truncate this chunk to fit
                remaining_tokens = max_tokens - tokens_used - 50  # Buffer
                if remaining_tokens > 100:
                    truncated = self._truncate_to_tokens(chunk_text, remaining_tokens)
                    lines.append(truncated)
                    chunks_included += 1
                break
            
            lines.append(chunk_text)
            lines.append("")  # Blank line between chunks
            tokens_used += chunk_tokens
            chunks_included += 1
        
        lines.extend([
            "",
            "=" * 60,
            f"END OF CONTEXT ({chunks_included} passages)",
            "=" * 60,
            "",
        ])
        
        return "\n".join(lines)
    
    def _build_context_section(
        self,
        context_docs: List[ContextDocument],
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Build the context section to prepend to the prompt.
        
        Args:
            context_docs: Documents to include as context
            max_tokens: Max tokens for context section
        
        Returns:
            Formatted context section string
        """
        if not context_docs:
            return ""
        
        max_tokens = max_tokens or self.context_max_tokens
        
        lines = [
            "=" * 60,
            "CONTEXT FROM YOUR DOCUMENTS",
            "The following documents from your local files may be relevant:",
            "=" * 60,
            "",
        ]
        
        tokens_used = self._estimate_tokens("\n".join(lines))
        docs_included = 0
        
        for i, doc in enumerate(context_docs, 1):
            doc_text = self._format_context_document(doc, i)
            doc_tokens = self._estimate_tokens(doc_text)
            
            if tokens_used + doc_tokens > max_tokens:
                # Truncate this document to fit
                remaining_tokens = max_tokens - tokens_used - 50  # Buffer
                if remaining_tokens > 100:
                    truncated = self._truncate_to_tokens(doc_text, remaining_tokens)
                    lines.append(truncated)
                    docs_included += 1
                break
            
            lines.append(doc_text)
            lines.append("")  # Blank line between docs
            tokens_used += doc_tokens
            docs_included += 1
        
        lines.extend([
            "",
            "=" * 60,
            f"END OF CONTEXT ({docs_included} documents)",
            "=" * 60,
            "",
        ])
        
        return "\n".join(lines)
    
    def enrich_prompt(
        self,
        prompt: str,
        max_context_docs: Optional[int] = None,
        max_context_tokens: Optional[int] = None,
        max_context_chunks: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        use_chunks: Optional[bool] = None,
    ) -> RAGResult:
        """
        Enrich a user prompt with relevant context from indexed documents.
        
        This is the main entry point for RAG. It:
        1. Searches for relevant chunks (preferred) or documents (fallback)
        2. Formats the context section
        3. Prepends context to the user's prompt
        4. Returns both the enriched prompt and the context sources
        
        Args:
            prompt: The user's original prompt
            max_context_docs: Override max documents to include (fallback mode)
            max_context_tokens: Override max tokens for context section
            max_context_chunks: Override max chunks to include (preferred mode)
            filters: Optional search filters (only for document fallback)
            system_instruction: Optional instruction to add before context
            use_chunks: Override config to force chunk/document mode
        
        Returns:
            RAGResult with enriched prompt and context information
        """
        start_time = time.time()
        
        # Determine retrieval mode
        should_use_chunks = use_chunks if use_chunks is not None else self.use_chunks
        
        self.logger.info(
            "Enriching prompt with RAG context",
            metadata={
                "prompt_length": len(prompt),
                "mode": "chunks" if should_use_chunks else "documents",
            }
        )
        
        context_docs: List[ContextDocument] = []
        context_chunks: List[ContextChunk] = []
        context_section = ""
        mode = "documents"
        
        # Try chunk-based retrieval first (US-023)
        if should_use_chunks:
            context_chunks = self.search_chunks_context(
                query=prompt,
                max_chunks=max_context_chunks or self.max_context_chunks,
            )
            
            if context_chunks:
                mode = "chunks"
                context_section = self._build_chunks_context_section(
                    context_chunks,
                    max_tokens=max_context_tokens,
                )
        
        # Fallback to document-based retrieval
        if not context_section:
            context_docs = self.search_context(
                query=prompt,
                max_docs=max_context_docs,
                filters=filters,
            )
            mode = "documents"
            context_section = self._build_context_section(
                context_docs,
                max_tokens=max_context_tokens,
            )
        
        search_time_ms = (time.time() - start_time) * 1000
        
        # Build enriched prompt
        parts = []
        
        if system_instruction:
            parts.append(system_instruction)
            parts.append("")
        
        if context_section:
            parts.append(context_section)
        
        parts.append(prompt)
        
        enriched_prompt = "\n".join(parts)
        
        # Estimate total context tokens
        total_context_tokens = self._estimate_tokens(context_section)
        
        # Log with mode-specific info
        context_count = len(context_chunks) if mode == "chunks" else len(context_docs)
        self.logger.info(
            "Prompt enriched successfully",
            metadata={
                "mode": mode,
                "context_items": context_count,
                "context_tokens": total_context_tokens,
                "search_time_ms": round(search_time_ms, 2),
            }
        )
        
        return RAGResult(
            original_prompt=prompt,
            enriched_prompt=enriched_prompt,
            context_docs=context_docs,
            context_chunks=context_chunks,
            total_context_tokens=total_context_tokens,
            search_time_ms=search_time_ms,
            mode=mode,
        )
    
    def enrich_messages(
        self,
        messages: List[Dict[str, str]],
        max_context_docs: Optional[int] = None,
        max_context_tokens: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[Dict[str, str]], List[ContextDocument], float]:
        """
        Enrich a list of chat messages with RAG context.
        
        For chat-style APIs (Ollama, OpenAI), this enriches the last
        user message with context while preserving conversation history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_context_docs: Override max documents
            max_context_tokens: Override max tokens
            filters: Optional search filters
        
        Returns:
            Tuple of (enriched_messages, context_docs, search_time_ms)
        """
        if not messages:
            return messages, [], 0.0
        
        # Find the last user message
        last_user_idx = None
        last_user_content = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                last_user_idx = i
                last_user_content = messages[i].get("content", "")
                break
        
        if last_user_idx is None or not last_user_content:
            return messages, [], 0.0
        
        # Enrich the last user message
        result = self.enrich_prompt(
            prompt=last_user_content,
            max_context_docs=max_context_docs,
            max_context_tokens=max_context_tokens,
            filters=filters,
        )
        
        # Create enriched messages list
        enriched_messages = messages.copy()
        enriched_messages[last_user_idx] = {
            "role": "user",
            "content": result.enriched_prompt,
        }
        
        return enriched_messages, result.context_docs, result.search_time_ms
