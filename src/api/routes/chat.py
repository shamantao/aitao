"""
Chat API route for AItao.

Provides chat endpoints compatible with both Ollama and OpenAI formats.
Integrates RAG context enrichment before forwarding to LLM backend.

Endpoints:
- POST /api/chat        - Ollama-compatible chat
- POST /v1/chat/completions - OpenAI-compatible chat

Workflow:
1. Receive chat request
2. Enrich with RAG context (optional, controlled by rag_enabled)
3. Forward to Ollama
4. Stream response back to client
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.core.config import ConfigManager, get_config
from src.core.logger import get_logger
from src.llm.ollama_client import (
    OllamaClient,
    OllamaChatMessage,
    OllamaConnectionError,
    OllamaModelNotFound,
)
from src.llm.rag_engine import RAGEngine, ContextDocument
from src.api.virtual_models import resolve_model, ResolvedModel

logger = get_logger("api.chat")

# Router
router = APIRouter(prefix="/api", tags=["Chat"])


# ============================================================================
# RAG System Context Helper
# ============================================================================

def _build_rag_system_context() -> str:
    """
    Build a system prompt combining identity, user profile and indexed directories.

    Sections (in order of priority):
    1. AItao identity  (who_is_Aitao from config)
    2. User profile    (who_are_you from config)
    3. Indexed paths   (indexing.include_paths from config)

    Placing identity and user profile first ensures every LLM call has
    the right persona and addressee context before any RAG chunks arrive.

    Returns:
        A formatted system prompt string, or an empty string if nothing
        is configured.
    """
    try:
        config = get_config()

        # 1. AItao identity
        who_is_aitao: str = config.get("who_is_Aitao", "").strip()

        # 2. User profile
        who_are_you: str = config.get("who_are_you", "").strip()

        # 3. Indexed directories
        indexing = config.get_section("indexing") or {}
        include_paths: list = indexing.get("include_paths", [])

        parts: list[str] = []

        if who_is_aitao:
            parts.append(who_is_aitao)

        if who_are_you:
            parts.append(f"About the user: {who_are_you}")

        if include_paths:
            paths_str = "\n".join(f"  - {p}" for p in include_paths)
            parts.append(
                "The RAG system indexes documents from the following directories "
                "configured by the user:\n"
                f"{paths_str}\n"
                "When asked which directories or files you have access to, "
                "list these configured paths."
            )

        return "\n\n".join(parts)
    except Exception:
        return ""


def _extract_conversation_attachments(messages: List) -> str:
    """
    Extract text from multimodal user messages (file attachments) in prior turns.

    When a client attaches a file, the message content arrives as a multimodal
    list.  On follow-up turns, RAG enrichment replaces the last user message
    with indexed-document context, which can overshadow the attached file that
    is already present in the conversation history.  This helper collects the
    file text so it can be re-injected as a persistent system context block,
    ensuring the LLM never "forgets" a file shared earlier in the session.

    Only user messages *before* the last user message are examined.

    Args:
        messages: Full list of ChatMessage objects from the current request.

    Returns:
        Concatenated attachment text (separated by ---), or empty string.
    """
    if len(messages) <= 1:
        return ""

    last_user_idx: Optional[int] = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == "user":
            last_user_idx = i
            break

    if last_user_idx is None or last_user_idx == 0:
        return ""

    parts: List[str] = []
    for i in range(last_user_idx):
        msg = messages[i]
        if msg.role != "user":
            continue
        # List-type content signals a client-side file or image attachment
        if isinstance(msg.content, list):
            text = _extract_text(msg.content)
            if text.strip():
                parts.append(text.strip())

    return "\n\n---\n\n".join(parts)


def _inject_rag_system_message(
    messages: list,
    system_context: str,
) -> list:
    """
    Inject or prepend the RAG system context into the message list.

    If a 'system' message already exists, the context is prepended to it.
    Otherwise a new 'system' message is inserted at position 0.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        system_context: The context string to inject.

    Returns:
        Updated message list.
    """
    if not system_context:
        return messages

    messages = list(messages)  # Shallow copy to avoid mutating original

    # Look for an existing system message
    for i, msg in enumerate(messages):
        if msg.get("role") == "system":
            existing = msg.get("content", "")
            messages[i] = {
                "role": "system",
                "content": f"{system_context}\n\n{existing}".strip(),
            }
            return messages

    # No system message found – insert one at the beginning
    messages.insert(0, {"role": "system", "content": system_context})
    return messages


# ============================================================================
# Request/Response Schemas
# ============================================================================

def _extract_text(content: Any) -> str:
    """
    Normalize OpenAI message content to a plain string.
    Handles: None, plain str, and multimodal list [{"type":"text","text":"..."}].
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Multimodal format: extract all text parts
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(parts)
    return str(content)


class ChatMessage(BaseModel):
    """Single chat message."""
    model_config = ConfigDict(extra="ignore")

    role: str = Field(..., description="Role: 'system', 'user', 'assistant'")
    content: Optional[Any] = Field(None, description="Message content (str or multimodal list)")


class ChatRequest(BaseModel):
    """Ollama-compatible chat request."""
    model: str = Field(..., description="Model name (e.g., 'qwen2.5-coder:7b')")
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    stream: bool = Field(default=True, description="Stream response")
    
    # RAG options
    rag_enabled: bool = Field(default=True, description="Enable RAG context enrichment")
    rag_max_docs: Optional[int] = Field(None, description="Max RAG context documents")
    
    # Model options (passed to Ollama)
    options: Optional[Dict[str, Any]] = Field(None, description="Model options")


class ChatResponseMessage(BaseModel):
    """Chat response message."""
    role: str = Field(default="assistant")
    content: str


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    model: str
    message: ChatResponseMessage
    created_at: str
    done: bool = True
    
    # RAG metadata
    rag_context: Optional[List[Dict[str, Any]]] = Field(
        None, description="RAG context documents used"
    )


class OpenAIChatRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model_config = ConfigDict(extra="ignore")  # Accept any extra OpenAI field silently

    model: str = Field(..., description="Model name")
    messages: List[ChatMessage] = Field(..., description="Messages")
    stream: bool = Field(default=False, description="Stream response")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None)

    # RAG extension (non-standard but useful)
    rag_enabled: bool = Field(default=True)


class OpenAIChoice(BaseModel):
    """OpenAI response choice."""
    index: int = 0
    message: ChatResponseMessage
    finish_reason: str = "stop"


class OpenAIChatResponse(BaseModel):
    """OpenAI-compatible chat response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    
    # RAG extension
    rag_context: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# Shared Components
# ============================================================================

_ollama_client: Optional[OllamaClient] = None
_rag_engine: Optional[RAGEngine] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client."""
    global _ollama_client
    if _ollama_client is None:
        from src.core.config import get_config
        config = get_config()
        _ollama_client = OllamaClient(config, logger)
    return _ollama_client


def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine."""
    global _rag_engine
    if _rag_engine is None:
        from src.core.config import get_config
        config = get_config()
        _rag_engine = RAGEngine(config, logger)
    return _rag_engine


def context_docs_to_dict(docs: List[ContextDocument]) -> List[Dict[str, Any]]:
    """Convert ContextDocument list to dict for JSON response."""
    return [
        {
            "id": doc.id,
            "path": doc.path,
            "title": doc.title,
            "score": doc.score,
            "category": doc.category,
        }
        for doc in docs
    ]


# ============================================================================
# Ollama-Compatible Endpoint
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Ollama-compatible chat completion.
    
    Enriches the conversation with RAG context before forwarding to Ollama.
    Supports both streaming and non-streaming responses.
    
    Virtual Model Support:
        Model names with suffixes like -basic, -context, -doc control RAG behavior:
        - llama3.1-basic: No RAG, pure LLM
        - llama3.1-doc: Full RAG with all documents
        - qwen-coder-context: RAG filtered to code/config categories
    """
    start_time = time.time()
    
    # Resolve virtual model to real model + RAG config
    resolved = resolve_model(request.model)
    
    # Determine effective RAG settings
    # Virtual model config overrides request if it's a virtual model
    effective_rag_enabled = resolved.rag_enabled if resolved.is_virtual else request.rag_enabled
    effective_filter = resolved.filter_categories if resolved.is_virtual else None
    
    logger.info(
        "Chat request received",
        metadata={
            "model": request.model,
            "real_model": resolved.real_model,
            "is_virtual": resolved.is_virtual,
            "message_count": len(request.messages),
            "stream": request.stream,
            "rag_enabled": effective_rag_enabled,
            "filter_categories": effective_filter,
        }
    )
    
    try:
        ollama = get_ollama_client()
        
        # Convert messages (content can be None or multimodal list)
        messages = [
            OllamaChatMessage(role=m.role, content=_extract_text(m.content))
            for m in request.messages
        ]
        
        # RAG enrichment (controlled by virtual model or request)
        context_docs = []
        if effective_rag_enabled and messages:
            try:
                rag = get_rag_engine()
                # Convert to dict format for enrich_messages
                msg_dicts = [{"role": m.role, "content": _extract_text(m.content)} for m in request.messages]
                # Inject RAG system context (include_paths, etc.) so the LLM
                # knows which directories are configured, regardless of RAG hits
                rag_system_ctx = _build_rag_system_context()
                msg_dicts = _inject_rag_system_message(msg_dicts, rag_system_ctx)
                # Re-inject file attachments from prior turns so the LLM
                # keeps them in scope even after RAG enriches the last message
                # (fix for issue #3 – conversation context loss)
                conv_files = _extract_conversation_attachments(request.messages)
                if conv_files:
                    note = (
                        "Content shared by the user earlier in this conversation "
                        "(use as primary reference for follow-up questions):\n\n"
                        + conv_files
                    )
                    for _m in msg_dicts:
                        if _m.get("role") == "system":
                            _m["content"] = _m["content"] + "\n\n" + note
                            break
                    else:
                        msg_dicts.insert(0, {"role": "system", "content": note})
                # Build filters dict if category filter specified
                filters = {"category": effective_filter} if effective_filter else None
                enriched_msgs, context_docs, _ = rag.enrich_messages(
                    msg_dicts,
                    max_context_docs=request.rag_max_docs,
                    filters=filters,
                )
                # Convert back to OllamaChatMessage
                messages = [
                    OllamaChatMessage(role=m["role"], content=m["content"])
                    for m in enriched_msgs
                ]
                logger.debug(
                    "RAG enrichment complete",
                    metadata={"context_docs": len(context_docs)}
                )
            except Exception as e:
                logger.warning(f"RAG enrichment failed, proceeding without: {e}")
        
        # Streaming response - use real model
        if request.stream:
            return StreamingResponse(
                _stream_chat_response(ollama, messages, request, context_docs, resolved),
                media_type="application/x-ndjson",
            )
        
        # Non-streaming response - use real model
        response = ollama.chat(
            messages=messages,
            model=resolved.real_model,
            stream=False,
            options=request.options,
        )
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Chat completed",
            metadata={"duration_ms": round(duration_ms, 2)}
        )
        
        return ChatResponse(
            model=request.model,  # Return original name (virtual or real)
            message=ChatResponseMessage(
                role="assistant",
                content=response.get("message", {}).get("content", ""),
            ),
            created_at=datetime.now(timezone.utc).isoformat(),
            rag_context=context_docs_to_dict(context_docs) if context_docs else None,
        )
        
    except OllamaConnectionError as e:
        logger.error(f"Ollama connection error: {e}")
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {e}")
    except OllamaModelNotFound as e:
        logger.error(f"Model not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


async def _stream_chat_response(
    ollama: OllamaClient,
    messages: List[OllamaChatMessage],
    request: ChatRequest,
    context_docs: List[ContextDocument],
    resolved: ResolvedModel,
) -> AsyncGenerator[str, None]:
    """Generate streaming chat response in Ollama format."""
    try:
        # First, send RAG context metadata if available
        if context_docs:
            rag_info = {
                "rag_context": context_docs_to_dict(context_docs),
                "done": False,
            }
            yield json.dumps(rag_info) + "\n"
        
        # Stream from Ollama using real model
        for chunk in ollama.chat(
            messages=messages,
            model=resolved.real_model,
            stream=True,
            options=request.options,
        ):
            yield chunk + "\n"
            
    except Exception as e:
        error_response = {"error": str(e), "done": True}
        yield json.dumps(error_response) + "\n"


# ============================================================================
# OpenAI-Compatible Endpoint
# ============================================================================

openai_router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


@openai_router.post("/chat/completions", response_model=OpenAIChatResponse)
async def openai_chat_completion(request: OpenAIChatRequest):
    """
    OpenAI-compatible chat completion endpoint.
    
    Allows tools expecting OpenAI API format to work with AItao.
    Supports virtual model routing for RAG control.
    """
    start_time = time.time()
    
    # Resolve virtual model to real model + RAG config
    resolved = resolve_model(request.model)
    
    # Determine effective RAG settings
    effective_rag_enabled = resolved.rag_enabled if resolved.is_virtual else request.rag_enabled
    effective_filter = resolved.filter_categories if resolved.is_virtual else None
    
    logger.info(
        "OpenAI-format chat request",
        metadata={
            "model": request.model,
            "real_model": resolved.real_model,
            "is_virtual": resolved.is_virtual,
            "message_count": len(request.messages),
            "stream": request.stream,
            "rag_enabled": effective_rag_enabled,
        }
    )
    
    try:
        ollama = get_ollama_client()
        
        # Convert messages (content can be None or multimodal list)
        messages = [
            OllamaChatMessage(role=m.role, content=_extract_text(m.content))
            for m in request.messages
        ]
        
        # RAG enrichment (controlled by virtual model or request)
        context_docs = []
        if effective_rag_enabled and messages:
            try:
                rag = get_rag_engine()
                msg_dicts = [{"role": m.role, "content": _extract_text(m.content)} for m in request.messages]
                # Inject RAG system context (include_paths, etc.) so the LLM
                # knows which directories are configured, regardless of RAG hits
                rag_system_ctx = _build_rag_system_context()
                msg_dicts = _inject_rag_system_message(msg_dicts, rag_system_ctx)
                # Re-inject file attachments from prior turns (fix for issue #3)
                conv_files = _extract_conversation_attachments(request.messages)
                if conv_files:
                    note = (
                        "Content shared by the user earlier in this conversation "
                        "(use as primary reference for follow-up questions):\n\n"
                        + conv_files
                    )
                    for _m in msg_dicts:
                        if _m.get("role") == "system":
                            _m["content"] = _m["content"] + "\n\n" + note
                            break
                    else:
                        msg_dicts.insert(0, {"role": "system", "content": note})
                # Build filters dict if category filter specified
                filters = {"category": effective_filter} if effective_filter else None
                enriched_msgs, context_docs, _ = rag.enrich_messages(
                    msg_dicts,
                    filters=filters,
                )
                messages = [
                    OllamaChatMessage(role=m["role"], content=m["content"])
                    for m in enriched_msgs
                ]
            except Exception as e:
                logger.warning(f"RAG enrichment failed: {e}")
        
        # Build Ollama options from OpenAI params
        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        
        # Streaming response
        if request.stream:
            return StreamingResponse(
                _stream_openai_response(ollama, messages, request, options, context_docs, resolved),
                media_type="text/event-stream",
            )
        
        # Non-streaming response - use real model
        response = ollama.chat(
            messages=messages,
            model=resolved.real_model,
            stream=False,
            options=options if options else None,
        )
        
        content = response.get("message", {}).get("content", "")
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "OpenAI chat completed",
            metadata={"duration_ms": round(duration_ms, 2)}
        )
        
        return OpenAIChatResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,  # Return original name (virtual or real)
            choices=[
                OpenAIChoice(
                    index=0,
                    message=ChatResponseMessage(role="assistant", content=content),
                    finish_reason="stop",
                )
            ],
            rag_context=context_docs_to_dict(context_docs) if context_docs else None,
        )
        
    except OllamaConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {e}")
    except OllamaModelNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"OpenAI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_openai_response(
    ollama: OllamaClient,
    messages: List[OllamaChatMessage],
    request: OpenAIChatRequest,
    options: Dict[str, Any],
    context_docs: List[ContextDocument],
    resolved: ResolvedModel,
) -> AsyncGenerator[str, None]:
    """Generate streaming response in OpenAI SSE format."""
    try:
        # Stream from Ollama using real model
        for chunk in ollama.chat(
            messages=messages,
            model=resolved.real_model,
            stream=True,
            options=options if options else None,
        ):
            # Parse Ollama chunk and convert to OpenAI format
            try:
                data = json.loads(chunk)
                content = data.get("message", {}).get("content", "")
                done = data.get("done", False)
                
                openai_chunk = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,  # Return original name
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": content} if content else {},
                            "finish_reason": "stop" if done else None,
                        }
                    ],
                }
                
                yield f"data: {json.dumps(openai_chunk)}\n\n"
                
                if done:
                    yield "data: [DONE]\n\n"
                    break
                    
            except json.JSONDecodeError:
                continue
                
    except Exception as e:
        error_chunk = {"error": {"message": str(e)}}
        yield f"data: {json.dumps(error_chunk)}\n\n"
