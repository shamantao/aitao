"""
Models API route for AItao.

Provides model listing endpoints compatible with both Ollama and OpenAI formats.
Fetches available models from the Ollama backend and exposes them via API.

Endpoints:
- GET /api/tags    - Ollama-compatible model list
- GET /v1/models   - OpenAI-compatible model list

These endpoints allow clients (Continue.dev, AnythingLLM, etc.) to discover
which models are available for chat and completion requests.
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.llm.ollama_client import OllamaClient, OllamaConnectionError

logger = get_logger("api.models")

# Routers
router = APIRouter(prefix="/api", tags=["Models"])
openai_router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


# ============================================================================
# Shared Components
# ============================================================================

_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client."""
    global _ollama_client
    if _ollama_client is None:
        from src.core.config import get_config
        config = get_config()
        _ollama_client = OllamaClient(config, logger)
    return _ollama_client


# ============================================================================
# Response Schemas
# ============================================================================

class OllamaModelDetails(BaseModel):
    """Ollama model details."""
    format: Optional[str] = None
    family: Optional[str] = None
    families: Optional[List[str]] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None


class OllamaModel(BaseModel):
    """Single model in Ollama format."""
    name: str = Field(..., description="Model name (e.g., 'qwen2.5-coder:7b')")
    modified_at: str = Field(..., description="Last modified timestamp")
    size: int = Field(..., description="Model size in bytes")
    digest: str = Field(..., description="Model digest/hash")
    details: Optional[OllamaModelDetails] = None


class OllamaModelsResponse(BaseModel):
    """Ollama-compatible models list response."""
    models: List[OllamaModel]


class OpenAIModel(BaseModel):
    """Single model in OpenAI format."""
    id: str = Field(..., description="Model identifier")
    object: str = Field(default="model")
    created: int = Field(..., description="Creation timestamp")
    owned_by: str = Field(default="aitao")


class OpenAIModelsResponse(BaseModel):
    """OpenAI-compatible models list response."""
    object: str = Field(default="list")
    data: List[OpenAIModel]


# ============================================================================
# Ollama-Compatible Endpoints
# ============================================================================

@router.get("/tags", response_model=OllamaModelsResponse)
async def list_models_ollama():
    """
    List available models (Ollama-compatible format).
    
    Returns all models available in the Ollama backend.
    This endpoint is compatible with Ollama API clients.
    """
    logger.info("Listing models (Ollama format)")
    
    try:
        ollama = get_ollama_client()
        models_data = ollama.list_models()
        
        # Parse the response from Ollama
        models = []
        for model_info in models_data.get("models", []):
            # Extract details if present
            details = None
            if "details" in model_info:
                details = OllamaModelDetails(
                    format=model_info["details"].get("format"),
                    family=model_info["details"].get("family"),
                    families=model_info["details"].get("families"),
                    parameter_size=model_info["details"].get("parameter_size"),
                    quantization_level=model_info["details"].get("quantization_level"),
                )
            
            models.append(OllamaModel(
                name=model_info.get("name", "unknown"),
                modified_at=model_info.get("modified_at", ""),
                size=model_info.get("size", 0),
                digest=model_info.get("digest", ""),
                details=details,
            ))
        
        logger.info(f"Found {len(models)} models")
        return OllamaModelsResponse(models=models)
        
    except OllamaConnectionError as e:
        logger.error(f"Cannot connect to Ollama: {e}")
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {e}")
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")


@router.get("/show/{model_name}")
async def show_model_info(model_name: str):
    """
    Get detailed information about a specific model.
    
    Ollama-compatible endpoint for model details.
    """
    logger.info(f"Getting info for model: {model_name}")
    
    try:
        ollama = get_ollama_client()
        model_info = ollama.show_model(model_name)
        return model_info
        
    except OllamaConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {e}")
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")


# ============================================================================
# OpenAI-Compatible Endpoints
# ============================================================================

@openai_router.get("/models", response_model=OpenAIModelsResponse)
async def list_models_openai():
    """
    List available models (OpenAI-compatible format).
    
    Converts Ollama models to OpenAI format for compatibility with
    OpenAI API clients like Continue.dev.
    """
    logger.info("Listing models (OpenAI format)")
    
    try:
        ollama = get_ollama_client()
        models_data = ollama.list_models()
        
        # Convert to OpenAI format
        models = []
        for model_info in models_data.get("models", []):
            model_name = model_info.get("name", "unknown")
            
            # Parse modified_at to timestamp if available
            created = int(time.time())
            if "modified_at" in model_info:
                try:
                    from datetime import datetime
                    # Ollama uses ISO format
                    dt = datetime.fromisoformat(
                        model_info["modified_at"].replace("Z", "+00:00")
                    )
                    created = int(dt.timestamp())
                except (ValueError, TypeError):
                    pass
            
            models.append(OpenAIModel(
                id=model_name,
                object="model",
                created=created,
                owned_by="ollama",
            ))
        
        logger.info(f"Returning {len(models)} models in OpenAI format")
        return OpenAIModelsResponse(object="list", data=models)
        
    except OllamaConnectionError as e:
        logger.error(f"Cannot connect to Ollama: {e}")
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {e}")
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@openai_router.get("/models/{model_id}")
async def get_model_openai(model_id: str):
    """
    Get a specific model (OpenAI-compatible format).
    
    Returns model info in OpenAI format.
    """
    logger.info(f"Getting model: {model_id}")
    
    try:
        ollama = get_ollama_client()
        model_info = ollama.show_model(model_id)
        
        return OpenAIModel(
            id=model_id,
            object="model",
            created=int(time.time()),
            owned_by="ollama",
        )
        
    except OllamaConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
