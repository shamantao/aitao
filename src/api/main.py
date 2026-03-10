"""
FastAPI REST API application for AItao V2.

This module provides the main FastAPI application with:
- CORS middleware configuration
- Request logging
- Error handlers
- API routes for search, ingest, health, stats, chat, and models
- OpenAPI documentation at /docs

Endpoints:
- GET  /api/health         - System health check
- GET  /api/stats          - Index statistics
- POST /api/search         - Hybrid search
- POST /api/ingest         - Queue file for indexing
- POST /api/chat           - Chat with RAG (Ollama-compatible)
- POST /v1/chat/completions - Chat with RAG (OpenAI-compatible)
- GET  /api/tags           - List models (Ollama-compatible)
- GET  /v1/models          - List models (OpenAI-compatible)
"""

import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import schemas
from src.api.schemas import (
    SearchRequest, SearchResponse,
    IngestRequest, IngestResponse, IngestBatchRequest, IngestBatchResponse,
    HealthResponse, StatsResponse, ErrorResponse
)

# Import core modules
try:
    from src.core.config import ConfigManager
    from src.core.logger import get_logger
except ImportError:
    from core.config import ConfigManager
    from core.logger import get_logger

# Version
try:
    from src.core.version import get_version
except ImportError:
    from core.version import get_version

__version__ = get_version()

# Logger
logger = get_logger("api")

# Global state
_start_time: Optional[float] = None
_config: Optional[ConfigManager] = None


def get_app_config() -> ConfigManager:
    """Get or create config manager instance via singleton."""
    global _config
    if _config is None:
        from src.core.config import get_config
        _config = get_config()
    return _config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    global _start_time
    _start_time = time.time()
    logger.info("AItao API starting", metadata={"version": __version__})
    yield
    logger.info("AItao API shutting down")


# Create FastAPI app
app = FastAPI(
    title="AItao API",
    description="Local RAG system for document indexing and semantic search",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


def configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware from config."""
    config = get_app_config()

    # Default to wildcard: local clients (OnlyOffice, Continue.dev, etc.) use
    # non-http origins (onlyoffice://, vscode-webview://, ...) that must be allowed.
    # allow_credentials must be False when allow_origins=["*"] (CORS standard).
    # AItao uses Bearer tokens only — cookie credentials are not needed.
    cors_origins = config.get("api.cors_origins", ["*"])
    if isinstance(cors_origins, str):
        cors_origins = [cors_origins]

    allow_credentials = "*" not in cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS configured", metadata={"origins": cors_origins})


# Configure CORS
configure_cors(app)


# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log request (skip health checks for less noise)
    if request.url.path != "/api/health":
        logger.info(
            f"{request.method} {request.url.path}",
            metadata={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client": request.client.host if request.client else "unknown",
            }
        )
    
    # Add timing header
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    return response


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standard error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP_{exc.status_code}",
            message=exc.detail,
            timestamp=datetime.now(timezone.utc),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", metadata={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_ERROR",
            message="An unexpected error occurred",
            timestamp=datetime.now(timezone.utc),
        ).model_dump(mode="json"),
    )


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs."""
    return {"message": "AItao API", "version": __version__, "docs": "/docs"}


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Check API health status (FAST).
    
    Returns instantly - API is responding? Yes/No.
    Does NOT check dependent services (LanceDB, Meilisearch, Worker).
    
    Use this endpoint for monitoring and load balancing.
    Response time: < 50ms
    """
    from src.api.routes.health import check_health
    return await check_health(_start_time, __version__)


@app.get("/api/health/debug", response_model=HealthResponse, tags=["System"])
async def health_check_debug():
    """
    Check ALL services health status (SLOW - use for diagnostics only).
    
    Performs detailed diagnostics on:
    - API status
    - LanceDB connectivity and document count
    - Meilisearch connectivity and index status
    - Worker daemon status
    
    WARNING: This endpoint is SLOW (~2+ seconds) because it loads all documents
    from LanceDB for statistics. Do NOT use for monitoring/load balancing.
    
    Use /api/health for monitoring. Use this endpoint only for debugging.
    Response time: 2-3+ seconds depending on index size
    """
    from src.api.routes.health import check_health_debug
    return await check_health_debug(_start_time, __version__)


@app.get("/api/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    """
    Get index statistics.
    
    Returns document counts and storage usage for all indexes.
    """
    from src.api.routes.stats import get_index_stats
    return await get_index_stats()


@app.post("/api/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest):
    """
    Search documents using hybrid search.
    
    Combines full-text search (Meilisearch) with semantic search (LanceDB)
    for best results. Supports filtering by path, category, language, and date.
    """
    from src.api.routes.search import perform_search
    return await perform_search(request)


@app.post("/api/ingest", response_model=IngestResponse, tags=["Indexing"])
async def ingest_file(request: IngestRequest):
    """
    Queue a file for indexing.
    
    The file will be added to the processing queue and indexed asynchronously.
    """
    from src.api.routes.ingest import queue_file
    return await queue_file(request)


@app.post("/api/ingest/batch", response_model=IngestBatchResponse, tags=["Indexing"])
async def ingest_batch(request: IngestBatchRequest):
    """
    Queue multiple files for indexing.
    
    All files will be added to the processing queue with the specified priority.
    """
    from src.api.routes.ingest import queue_batch
    return await queue_batch(request)


# ============================================================================
# Chat Routes (mounted via router)
# ============================================================================

# Import and include chat routes
from src.api.routes.chat import router as chat_router, openai_router
app.include_router(chat_router)
app.include_router(openai_router)


# ============================================================================
# Models Routes (mounted via router)
# ============================================================================

# Import and include models routes
from src.api.routes.models import router as models_router, openai_router as models_openai_router
app.include_router(models_router)
app.include_router(models_openai_router)


# ============================================================================
# Main Entry Point
# ============================================================================

def run_server(host: str = "127.0.0.1", port: int = 5000, reload: bool = False):
    """Run the API server with uvicorn."""
    import uvicorn
    
    config = get_app_config()
    host = config.get("api.host", host)
    port = config.get("api.port", port)
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run_server()
