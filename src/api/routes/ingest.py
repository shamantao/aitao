"""
Ingest endpoint handler.

This module provides file ingestion functionality:
- Queue single file for indexing
- Queue batch of files
- Validation and error handling
"""

import os
from pathlib import Path
from typing import List

from fastapi import HTTPException

from src.api.schemas import (
    IngestRequest, IngestResponse,
    IngestBatchRequest, IngestBatchResponse,
)
from src.core.logger import get_logger

logger = get_logger("api.ingest")


def validate_file_path(file_path: str) -> Path:
    """
    Validate that a file path exists and is readable.
    
    Args:
        file_path: Path to validate
    
    Returns:
        Path object if valid
    
    Raises:
        HTTPException if invalid
    """
    path = Path(file_path)
    
    if not path.is_absolute():
        raise HTTPException(
            status_code=400,
            detail=f"Path must be absolute: {file_path}"
        )
    
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}"
        )
    
    if not path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a file: {file_path}"
        )
    
    if not os.access(path, os.R_OK):
        raise HTTPException(
            status_code=403,
            detail=f"File is not readable: {file_path}"
        )
    
    return path


async def queue_file(request: IngestRequest) -> IngestResponse:
    """
    Queue a single file for indexing.
    
    Args:
        request: Ingest request with file path and options
    
    Returns:
        IngestResponse with task details
    """
    # Validate file
    path = validate_file_path(request.file_path)
    
    logger.info(f"Ingest request: {path}", metadata={
        "priority": request.priority,
        "force": request.force,
    })
    
    try:
        from src.indexation.queue import TaskQueue
        queue = TaskQueue()
        
        # Check if already indexed (unless force=True)
        if not request.force:
            from src.indexation.indexer import DocumentIndexer
            indexer = DocumentIndexer()
            if indexer.is_indexed(str(path)):
                return IngestResponse(
                    success=True,
                    message="File already indexed (use force=True to re-index)",
                    file_path=str(path),
                )
        
        # Add to queue
        task_id = queue.add_task(
            file_path=str(path),
            task_type="index",
            priority=request.priority,
        )
        
        logger.info(f"File queued for indexing: {path}", metadata={"task_id": task_id})
        
        return IngestResponse(
            success=True,
            message="File queued for indexing",
            task_id=task_id,
            file_path=str(path),
        )
    
    except Exception as e:
        logger.error(f"Failed to queue file: {e}", metadata={"file": str(path)})
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue file: {str(e)}"
        )


async def queue_batch(request: IngestBatchRequest) -> IngestBatchResponse:
    """
    Queue multiple files for indexing.
    
    Args:
        request: Batch ingest request with file paths
    
    Returns:
        IngestBatchResponse with counts
    """
    logger.info(f"Batch ingest request: {len(request.file_paths)} files", metadata={
        "priority": request.priority,
    })
    
    queued = 0
    skipped = 0
    errors: List[str] = []
    
    try:
        from src.indexation.queue import TaskQueue
        queue = TaskQueue()
        
        for file_path in request.file_paths:
            try:
                # Validate file
                path = Path(file_path)
                
                if not path.exists():
                    errors.append(f"File not found: {file_path}")
                    skipped += 1
                    continue
                
                if not path.is_file():
                    errors.append(f"Not a file: {file_path}")
                    skipped += 1
                    continue
                
                # Add to queue
                queue.add_task(
                    file_path=str(path),
                    task_type="index",
                    priority=request.priority,
                )
                queued += 1
                
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")
                skipped += 1
        
        logger.info(f"Batch ingest complete: {queued} queued, {skipped} skipped")
        
        return IngestBatchResponse(
            success=len(errors) == 0,
            queued=queued,
            skipped=skipped,
            errors=errors[:10],  # Limit error messages
        )
    
    except Exception as e:
        logger.error(f"Batch ingest failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch ingest failed: {str(e)}"
        )
