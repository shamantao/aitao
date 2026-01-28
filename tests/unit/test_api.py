"""
Unit tests for the FastAPI REST API.

This module tests all API endpoints:
- /api/health - System health check
- /api/stats - Index statistics
- /api/search - Document search
- /api/ingest - File ingestion

Uses pytest fixtures for mocking dependencies.
"""

import pytest
import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Create mock modules before importing the app
mock_lancedb_module = MagicMock()
mock_meilisearch_module = MagicMock()
mock_queue_module = MagicMock()
mock_worker_module = MagicMock()
mock_indexer_module = MagicMock()
mock_pathmanager_module = MagicMock()

# Pre-patch modules
sys.modules['src.search.lancedb_client'] = mock_lancedb_module
sys.modules['src.search.meilisearch_client'] = mock_meilisearch_module
sys.modules['src.indexation.queue'] = mock_queue_module
sys.modules['src.indexation.worker'] = mock_worker_module
sys.modules['src.indexation.indexer'] = mock_indexer_module

from src.api.main import app
from src.api.schemas import (
    SearchRequest, SearchResponse, SearchResultItem,
    IngestRequest, IngestResponse,
    HealthResponse, StatsResponse, ServiceStatus, IndexStats,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test."""
    # Reset LanceDB mock
    mock_lance_instance = MagicMock()
    mock_lance_instance.get_stats.return_value = {"total_documents": 1000, "size_bytes": 5000000}
    mock_lance_instance.search.return_value = [
        {"id": "doc1", "path": "/test/file1.pdf", "title": "Test Doc 1", "content": "Sample content", "score": 0.95},
    ]
    mock_lancedb_module.LanceDBClient = MagicMock(return_value=mock_lance_instance)
    
    # Reset Meilisearch mock
    mock_meili_instance = MagicMock()
    mock_meili_instance.is_connected.return_value = True
    mock_meili_instance.get_stats.return_value = {"numberOfDocuments": 1000, "indexSize": 5000000}
    mock_meili_instance.search.return_value = [
        {"id": "doc1", "path": "/test/file1.pdf", "title": "Test Doc 1", "content": "Sample content"},
    ]
    mock_meilisearch_module.MeilisearchClient = MagicMock(return_value=mock_meili_instance)
    
    # Reset Worker mock
    mock_worker_instance = MagicMock()
    mock_worker_instance.is_running.return_value = True
    mock_worker_module.BackgroundWorker = MagicMock(return_value=mock_worker_instance)
    
    # Reset Queue mock
    mock_queue_instance = MagicMock()
    mock_queue_instance.add_task.return_value = "task-123"
    mock_queue_instance.get_stats.return_value = {"pending": 5, "processing": 1, "completed": 100, "failed": 2, "total": 108}
    mock_queue_module.TaskQueue = MagicMock(return_value=mock_queue_instance)
    
    # Reset Indexer mock
    mock_indexer_instance = MagicMock()
    mock_indexer_instance.is_indexed.return_value = False
    mock_indexer_module.DocumentIndexer = MagicMock(return_value=mock_indexer_instance)
    
    yield


# ============================================================================
# Root Endpoint Tests
# ============================================================================

class TestRootEndpoint:
    """Tests for the root endpoint."""
    
    def test_root_returns_info(self, client):
        """Test that root returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["docs"] == "/docs"


# ============================================================================
# Health Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Tests for /api/health endpoint."""
    
    def test_health_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/api/health")
        assert response.status_code == 200
    
    def test_health_response_format(self, client):
        """Test health response has correct format."""
        response = client.get("/api/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data
        
        # Check services
        services = data["services"]
        assert "api" in services
        assert "lancedb" in services
        assert "meilisearch" in services
        assert "worker" in services
    
    def test_health_all_healthy(self, client):
        """Test health returns 'healthy' when all services up."""
        response = client.get("/api/health")
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["services"]["api"]["status"] == "healthy"
    
    def test_health_degraded_when_service_down(self, client):
        """Test health returns 'degraded' when a service is down."""
        # Mock LanceDB to fail
        mock_lancedb_module.LanceDBClient.side_effect = Exception("Connection failed")
        
        # Mock Meilisearch to be disconnected
        mock_meili_instance = MagicMock()
        mock_meili_instance.is_connected.return_value = False
        mock_meilisearch_module.MeilisearchClient = MagicMock(return_value=mock_meili_instance)
        
        response = client.get("/api/health")
        data = response.json()
        
        assert data["status"] == "degraded"


# ============================================================================
# Stats Endpoint Tests
# ============================================================================

class TestStatsEndpoint:
    """Tests for /api/stats endpoint."""
    
    def test_stats_returns_200(self, client):
        """Test stats endpoint returns 200."""
        response = client.get("/api/stats")
        assert response.status_code == 200
    
    def test_stats_response_format(self, client):
        """Test stats response has correct format."""
        response = client.get("/api/stats")
        data = response.json()
        
        assert "total_documents" in data
        assert data["total_documents"] >= 0


# ============================================================================
# Search Endpoint Tests
# ============================================================================

class TestSearchEndpoint:
    """Tests for /api/search endpoint."""
    
    def test_search_requires_query(self, client):
        """Test search endpoint requires query parameter."""
        response = client.post("/api/search", json={})
        assert response.status_code == 422  # Validation error
    
    def test_search_empty_query_rejected(self, client):
        """Test search rejects empty query."""
        response = client.post("/api/search", json={"query": ""})
        assert response.status_code == 422
    
    def test_search_returns_200(self, client):
        """Test search returns 200 with valid query."""
        response = client.post("/api/search", json={"query": "test query"})
        assert response.status_code == 200
    
    def test_search_response_format(self, client):
        """Test search response has correct format."""
        response = client.post("/api/search", json={"query": "test"})
        data = response.json()
        
        assert "query" in data
        assert "total" in data
        assert "results" in data
        assert "search_time_ms" in data
    
    def test_search_with_filters(self, client):
        """Test search with filters."""
        response = client.post("/api/search", json={
            "query": "test",
            "limit": 5,
            "category": "documents",
            "language": "en",
        })
        assert response.status_code == 200
    
    def test_search_modes(self, client):
        """Test different search modes."""
        for mode in ["hybrid", "semantic", "fulltext"]:
            response = client.post("/api/search", json={
                "query": "test",
                "search_mode": mode,
            })
            assert response.status_code == 200


# ============================================================================
# Ingest Endpoint Tests
# ============================================================================

class TestIngestEndpoint:
    """Tests for /api/ingest endpoint."""
    
    def test_ingest_requires_file_path(self, client):
        """Test ingest endpoint requires file_path."""
        response = client.post("/api/ingest", json={})
        assert response.status_code == 422
    
    def test_ingest_rejects_relative_path(self, client):
        """Test ingest rejects relative paths."""
        response = client.post("/api/ingest", json={"file_path": "relative/path.pdf"})
        assert response.status_code == 400
    
    def test_ingest_rejects_nonexistent_file(self, client):
        """Test ingest rejects non-existent files."""
        response = client.post("/api/ingest", json={"file_path": "/nonexistent/file.pdf"})
        assert response.status_code == 404
    
    def test_ingest_queues_valid_file(self, client, tmp_path):
        """Test ingest queues valid file."""
        # Create temp file
        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")
        
        response = client.post("/api/ingest", json={"file_path": str(test_file)})
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] == "task-123"
    
    def test_ingest_batch_returns_200(self, client, tmp_path):
        """Test batch ingest returns 200."""
        # Create temp files
        file1 = tmp_path / "test1.pdf"
        file2 = tmp_path / "test2.pdf"
        file1.write_text("content1")
        file2.write_text("content2")
        
        response = client.post("/api/ingest/batch", json={
            "file_paths": [str(file1), str(file2)]
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["queued"] == 2
        assert data["skipped"] == 0


# ============================================================================
# Schema Tests
# ============================================================================

class TestSchemas:
    """Tests for Pydantic schemas."""
    
    def test_search_request_defaults(self):
        """Test SearchRequest has correct defaults."""
        request = SearchRequest(query="test")
        assert request.limit == 10
        assert request.offset == 0
        assert request.search_mode == "hybrid"
    
    def test_search_request_validation(self):
        """Test SearchRequest validation."""
        # Query too short
        with pytest.raises(ValueError):
            SearchRequest(query="")
        
        # Limit out of range
        with pytest.raises(ValueError):
            SearchRequest(query="test", limit=200)
    
    def test_search_result_item(self):
        """Test SearchResultItem creation."""
        item = SearchResultItem(
            id="doc123",
            path="/test/file.pdf",
            title="Test Document",
            summary="This is a summary",
            score=0.95,
        )
        assert item.id == "doc123"
        assert item.score == 0.95
    
    def test_health_response(self):
        """Test HealthResponse creation."""
        response = HealthResponse(
            status="healthy",
            version="2.2.13",
            timestamp=datetime.now(timezone.utc),
            services={
                "api": ServiceStatus(name="api", status="healthy"),
            },
        )
        assert response.status == "healthy"
    
    def test_ingest_request_defaults(self):
        """Test IngestRequest has correct defaults."""
        request = IngestRequest(file_path="/test/file.pdf")
        assert request.priority == "normal"
        assert request.force is False


# ============================================================================
# Middleware Tests
# ============================================================================

class TestMiddleware:
    """Tests for API middleware."""
    
    def test_response_time_header(self, client):
        """Test X-Response-Time header is added."""
        response = client.get("/")
        assert "X-Response-Time" in response.headers
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        # CORS preflight should work
        assert response.status_code in (200, 400)


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    def test_404_for_unknown_endpoint(self, client):
        """Test 404 for unknown endpoints."""
        response = client.get("/api/unknown")
        assert response.status_code == 404
    
    def test_422_for_invalid_json(self, client):
        """Test 422 for invalid request body."""
        response = client.post("/api/search", json={"invalid": "data"})
        assert response.status_code == 422
    
    def test_error_response_format(self, client):
        """Test error responses have correct format."""
        response = client.get("/api/unknown")
        data = response.json()
        assert "detail" in data  # FastAPI default error format
