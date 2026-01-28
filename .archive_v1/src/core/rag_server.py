#!/usr/bin/env python3
"""
RAG Server - AI Tao
Generic Document Search API (port 8200)

Provides a model-agnostic API endpoint for searching indexed documents.
Reads from local LanceDB (autonomous, no dependency on AnythingLLM).
Apps like VSCode, Wave Terminal, custom scripts can use this to access RAG.

This ensures AI Tao remains independent of AnythingLLM's UI or model choices.
"""

import os
import sys
from typing import List, Dict, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from src.core.path_manager import path_manager
    from src.core.logger import get_logger
    from src.core.kotaemon_indexer import AITaoIndexer
except ImportError:
    from core.path_manager import path_manager
    from core.logger import get_logger
    from core.kotaemon_indexer import AITaoIndexer

logger = get_logger("RAGServer", "rag_server.log")

# FastAPI App
app = FastAPI(
    title="AI Tao RAG Server",
    description="Generic document search API for external apps (local LanceDB)",
    version="1.0"
)


class RAGServer:
    """Handle document search queries against local LanceDB (AITaoIndexer)."""
    
    def __init__(self):
        self.indexer = AITaoIndexer(collection_name="default")
        self.config = path_manager.get_indexing_config()
        
        if self.indexer.is_enabled():
            logger.info("✅ RAG Server initialized with AITaoIndexer (LanceDB)")
        else:
            logger.warning("⚠️ RAG Server: Indexer not available. Search will return empty results.")
    
    def search(self, query: str, limit: int = 5, workspace: Optional[str] = None) -> List[Dict]:
        """Search documents using semantic similarity.
        
        Args:
            query: Search query text
            limit: Max results to return
            workspace: Filter by workspace name (optional, not enforced for LanceDB)
        
        Returns:
            List of matching documents with content and metadata
        """
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        try:
            # Use indexer's search method
            results = self.indexer.search(query, limit=limit)
            
            # Transform LanceDB results to API response format
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    "id": doc.get("id"),
                    "filename": doc.get("filename"),
                    "source": doc.get("path"),
                    "content": doc.get("content", "")[:500],  # Return first 500 chars
                    "workspace": workspace or "_default",
                    "metadata": {
                        "size_bytes": doc.get("size_bytes"),
                    }
                })
            
            logger.info(f"✅ Search '{query}' returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    
    def get_workspaces(self) -> List[Dict]:
        """List available workspaces. For LanceDB, return a single default workspace."""
        return [
            {
                "name": "_default",
                "slug": "default",
                "id": 0,
                "type": "default"
            }
        ]
    
    def get_workspace_stats(self, workspace: str) -> Dict:
        """Get document count and stats for a workspace."""
        try:
            stats = self.indexer.get_stats()
            return {
                "workspace": workspace,
                "document_count": stats.get("document_count", 0),
                "collection": stats.get("collection", "default")
            }
        except Exception as e:
            logger.error(f"Error getting workspace stats: {e}")
            return {"error": str(e)}


# Initialize server
rag_server = RAGServer()


# Routes

@app.get("/")
async def root():
    """Health check."""
    return {
        "status": "ok",
        "service": "AI Tao RAG Server",
        "version": "1.0",
        "backend": "LanceDB + sentence-transformers",
        "endpoints": {
            "search": "/v1/rag/search",
            "workspaces": "/v1/rag/workspaces",
            "stats": "/v1/rag/stats/{workspace}"
        }
    }


@app.post("/v1/rag/search")
async def search_documents(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(5, ge=1, le=100, description="Max results"),
    workspace: Optional[str] = Query(None, description="Filter by workspace")
):
    """Search indexed documents.
    
    Example:
        POST /v1/rag/search?query=tarifs&limit=5
        
    Returns:
        {
            "query": "tarifs",
            "results": [
                {
                    "filename": "pricing.md",
                    "source": "/path/to/pricing.md",
                    "content": "...",
                    "workspace": "_default"
                }
            ],
            "total": 1
        }
    """
    try:
        results = rag_server.search(query, limit, workspace)
        return {
            "query": query,
            "results": results,
            "total": len(results),
            "workspace_filter": workspace
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/rag/workspaces")
async def list_workspaces():
    """List all available workspaces.
    
    Returns:
        {
            "workspaces": [
                {"name": "_default", "slug": "default", "id": 0}
            ]
        }
    """
    workspaces = rag_server.get_workspaces()
    return {"workspaces": workspaces, "total": len(workspaces)}


@app.get("/v1/rag/stats/{workspace}")
async def get_stats(workspace: str):
    """Get statistics for a specific workspace.
    
    Returns:
        {"workspace": "_default", "document_count": 42}
    """
    stats = rag_server.get_workspace_stats(workspace)
    return stats


@app.get("/health")
async def health_check():
    """Kubernetes-style health check."""
    indexer_ready = rag_server.indexer.is_enabled()
    return {
        "status": "healthy" if indexer_ready else "degraded",
        "indexer_available": indexer_ready,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }


# Error handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Get RAG port from config
    rag_port = path_manager.get_config_value("server", "rag_port")
    if not rag_port:
        rag_port = 8200  # Default fallback
    else:
        rag_port = int(rag_port)
    
    logger.info(f"🚀 Starting RAG Server on port {rag_port}...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=rag_port,
        log_level="info"
    )
