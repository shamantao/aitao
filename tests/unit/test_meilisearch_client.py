"""
Unit tests for Meilisearch client.

Tests full-text search operations:
- Connection and initialization
- Document CRUD operations
- Full-text search with filters
- Statistics and index management

Note: These tests require a running Meilisearch instance at localhost:7700.
Tests use a dedicated test index that is cleaned up after each test.
"""

import hashlib
import pytest
import time
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from search.meilisearch_client import (
    MeilisearchClient,
    MeilisearchError,
    MeilisearchConnectionError,
    MEILISEARCH_AVAILABLE,
)


# Skip all tests if meilisearch package not installed
pytestmark = pytest.mark.skipif(
    not MEILISEARCH_AVAILABLE,
    reason="meilisearch package not installed"
)


def is_meilisearch_running() -> bool:
    """Check if Meilisearch server is available."""
    if not MEILISEARCH_AVAILABLE:
        return False
    try:
        from meilisearch import Client
        client = Client("http://localhost:7700")
        health = client.health()
        return health.get("status") == "available"
    except Exception:
        return False


# Skip tests if Meilisearch not running
requires_meilisearch = pytest.mark.skipif(
    not is_meilisearch_running(),
    reason="Meilisearch server not running at localhost:7700"
)


class TestMeilisearchClientInit:
    """Tests for MeilisearchClient initialization."""
    
    @requires_meilisearch
    def test_init_connects_to_server(self):
        """Test that initialization connects to Meilisearch server."""
        client = MeilisearchClient(
            index_name="test_init_index"
        )
        
        assert client.client is not None
        assert client.is_healthy()
        
        # Cleanup
        try:
            client.client.delete_index("test_init_index")
        except Exception:
            pass
    
    @requires_meilisearch
    def test_init_creates_index(self):
        """Test that initialization creates the index if missing."""
        test_index = "test_create_index"
        
        # Ensure index doesn't exist
        try:
            from meilisearch import Client
            c = Client("http://localhost:7700")
            c.delete_index(test_index)
            time.sleep(0.5)
        except Exception:
            pass
        
        client = MeilisearchClient(index_name=test_index)
        
        # Index should exist now
        assert client.index is not None
        assert client.index_name == test_index
        
        # Cleanup
        try:
            client.client.delete_index(test_index)
        except Exception:
            pass
    
    @requires_meilisearch
    def test_init_with_custom_host(self):
        """Test initialization with custom host."""
        client = MeilisearchClient(
            host="http://localhost:7700",
            index_name="test_custom_host"
        )
        
        assert client.host == "http://localhost:7700"
        
        # Cleanup
        try:
            client.client.delete_index("test_custom_host")
        except Exception:
            pass
    
    def test_init_fails_without_server(self):
        """Test that initialization fails when server not available."""
        with pytest.raises(MeilisearchConnectionError):
            MeilisearchClient(
                host="http://localhost:9999",  # Wrong port
                index_name="test_no_server"
            )
    
    @requires_meilisearch
    def test_get_version(self):
        """Test getting Meilisearch version."""
        client = MeilisearchClient(index_name="test_version")
        version = client.get_version()
        
        assert version != "unknown"
        # Version should be in format X.Y.Z
        assert "." in version
        
        # Cleanup
        try:
            client.client.delete_index("test_version")
        except Exception:
            pass


@requires_meilisearch
class TestMeilisearchClientCRUD:
    """Tests for document CRUD operations."""
    
    @pytest.fixture
    def client(self) -> Generator[MeilisearchClient, None, None]:
        """Create a test client with temporary index."""
        test_index = f"test_crud_{int(time.time())}"
        client = MeilisearchClient(index_name=test_index)
        yield client
        
        # Cleanup
        try:
            client.client.delete_index(test_index)
        except Exception:
            pass
    
    def test_generate_id(self, client):
        """Test ID generation from path."""
        path = "/documents/test.pdf"
        doc_id = client._generate_id(path)
        
        # Should be SHA256 hex
        assert len(doc_id) == 64
        assert all(c in "0123456789abcdef" for c in doc_id)
        
        # Same path should give same ID
        assert client._generate_id(path) == doc_id
    
    def test_add_document(self, client):
        """Test adding a document."""
        doc_id = client.add_document(
            path="/docs/test.pdf",
            title="Test Document",
            content="This is test content for the document.",
            category="documents",
            language="en",
            file_size=1024,
        )
        
        assert doc_id is not None
        assert len(doc_id) == 64  # SHA256 hex
        
        # Wait for indexing
        time.sleep(0.5)
        
        # Verify document exists
        doc = client.get_document(doc_id)
        assert doc is not None
        assert doc["title"] == "Test Document"
    
    def test_add_document_with_empty_content(self, client):
        """Test adding a document with empty content."""
        doc_id = client.add_document(
            path="/docs/empty.txt",
            title="Empty Document",
            content="",
        )
        
        assert doc_id is not None
    
    def test_get_document(self, client):
        """Test retrieving a document by ID."""
        path = "/docs/retrieve.pdf"
        doc_id = client.add_document(
            path=path,
            title="Retrievable Doc",
            content="Content to retrieve.",
            category="test",
        )
        
        # Wait for indexing
        time.sleep(0.5)
        
        result = client.get_document(doc_id)
        
        assert result is not None
        assert result["id"] == doc_id
        assert result["path"] == path
        assert result["title"] == "Retrievable Doc"
    
    def test_get_nonexistent_document(self, client):
        """Test getting a document that doesn't exist."""
        result = client.get_document("nonexistent_id_" + "0" * 50)
        assert result is None
    
    def test_delete_document(self, client):
        """Test deleting a document."""
        doc_id = client.add_document(
            path="/docs/delete_me.pdf",
            title="Delete Me",
            content="Document to be deleted.",
        )
        
        # Wait for indexing
        time.sleep(0.5)
        
        # Verify it exists
        assert client.get_document(doc_id) is not None
        
        # Delete it
        result = client.delete(doc_id)
        assert result is True
        
        # Wait for deletion
        time.sleep(0.5)
        
        # Verify it's gone
        assert client.get_document(doc_id) is None
    
    def test_delete_by_path(self, client):
        """Test deleting a document by path."""
        path = "/docs/delete_by_path.pdf"
        client.add_document(
            path=path,
            title="Delete by Path",
            content="Content here.",
        )
        
        # Wait for indexing
        time.sleep(0.5)
        
        result = client.delete_by_path(path)
        assert result is True
    
    def test_update_document(self, client):
        """Test that adding same path updates the document."""
        path = "/docs/update_me.pdf"
        
        # Add original
        doc_id1 = client.add_document(
            path=path,
            title="Original Title",
            content="Original content.",
        )
        
        # Wait for indexing
        time.sleep(0.5)
        
        # Add with same path (should update)
        doc_id2 = client.add_document(
            path=path,
            title="Updated Title",
            content="Updated content.",
        )
        
        # Same ID (same path)
        assert doc_id1 == doc_id2
        
        # Wait for update
        time.sleep(0.5)
        
        # Content should be updated
        result = client.get_document(doc_id1)
        assert result["title"] == "Updated Title"


@requires_meilisearch
class TestMeilisearchClientSearch:
    """Tests for full-text search functionality."""
    
    @pytest.fixture
    def client_with_docs(self) -> Generator[MeilisearchClient, None, None]:
        """Create client with sample documents."""
        test_index = f"test_search_{int(time.time())}"
        client = MeilisearchClient(index_name=test_index)
        
        # Add sample documents
        client.add_document(
            path="/docs/travel/paris.pdf",
            title="Paris Travel Guide",
            content="Paris is the capital of France. Visit the Eiffel Tower and Louvre museum.",
            category="travel",
            language="en",
        )
        
        client.add_document(
            path="/docs/tech/python.pdf",
            title="Python Programming",
            content="Python is a popular programming language. It's great for machine learning.",
            category="tech",
            language="en",
        )
        
        client.add_document(
            path="/docs/travel/berlin.pdf",
            title="Berlin City Guide",
            content="Berlin is the capital of Germany. Visit the Brandenburg Gate.",
            category="travel",
            language="en",
        )
        
        # Wait for indexing
        time.sleep(1)
        
        yield client
        
        # Cleanup
        try:
            client.client.delete_index(test_index)
        except Exception:
            pass
    
    def test_search_returns_results(self, client_with_docs):
        """Test that search returns relevant results."""
        results = client_with_docs.search("France travel", limit=5)
        
        assert len(results) > 0
        assert all("id" in r for r in results)
    
    def test_search_relevance(self, client_with_docs):
        """Test that most relevant results come first."""
        results = client_with_docs.search("Python programming", limit=3)
        
        # Python document should be in results
        paths = [r["path"] for r in results]
        assert "/docs/tech/python.pdf" in paths
    
    def test_search_with_category_filter(self, client_with_docs):
        """Test search with category filter."""
        results = client_with_docs.search(
            "capital",
            limit=10,
            filter_category="travel"
        )
        
        # All results should be in travel category
        assert all(r["category"] == "travel" for r in results)
    
    def test_search_with_limit(self, client_with_docs):
        """Test search respects limit parameter."""
        results = client_with_docs.search("guide", limit=1)
        assert len(results) <= 1
    
    def test_search_empty_query(self, client_with_docs):
        """Test search with empty query."""
        # Empty query should return documents (match all)
        results = client_with_docs.search("", limit=3)
        assert isinstance(results, list)
    
    def test_search_result_format(self, client_with_docs):
        """Test that search results have expected fields."""
        results = client_with_docs.search("Paris", limit=1)
        
        if results:
            result = results[0]
            assert "id" in result
            assert "path" in result
            assert "title" in result
            assert "content" in result
            assert "category" in result
    
    def test_search_typo_tolerance(self, client_with_docs):
        """Test that typo tolerance works."""
        # Search with typo
        results = client_with_docs.search("Pyton programing", limit=3)
        
        # Should still find Python document
        paths = [r["path"] for r in results]
        assert "/docs/tech/python.pdf" in paths


@requires_meilisearch
class TestMeilisearchClientStats:
    """Tests for statistics and index management."""
    
    @pytest.fixture
    def client(self) -> Generator[MeilisearchClient, None, None]:
        """Create a test client with temporary index."""
        test_index = f"test_stats_{int(time.time())}"
        client = MeilisearchClient(index_name=test_index)
        yield client
        
        # Cleanup
        try:
            client.client.delete_index(test_index)
        except Exception:
            pass
    
    def test_get_stats_empty_index(self, client):
        """Test statistics on empty index."""
        stats = client.get_stats()
        
        assert stats["total_documents"] == 0
        assert stats["is_indexing"] is False
        assert stats["index_name"] == client.index_name
    
    def test_get_stats_with_documents(self, client):
        """Test statistics with documents."""
        # Add documents
        client.add_document(
            path="/doc1.pdf",
            title="Doc 1",
            content="Content 1",
            category="travel",
            language="en",
        )
        client.add_document(
            path="/doc2.pdf",
            title="Doc 2",
            content="Content 2",
            category="tech",
            language="fr",
        )
        
        # Wait for indexing
        time.sleep(1)
        
        stats = client.get_stats()
        
        assert stats["total_documents"] == 2
        assert "field_distribution" in stats
    
    def test_clear_index(self, client):
        """Test clearing the index."""
        # Add documents
        client.add_document(path="/doc1.pdf", title="Doc 1", content="Content 1")
        client.add_document(path="/doc2.pdf", title="Doc 2", content="Content 2")
        
        # Wait for indexing
        time.sleep(1)
        
        # Verify they exist
        assert client.get_stats()["total_documents"] == 2
        
        # Clear
        count = client.clear()
        assert count == 2
        
        # Wait for clearing
        time.sleep(0.5)
        
        # Verify empty
        assert client.get_stats()["total_documents"] == 0


@requires_meilisearch
class TestMeilisearchClientBatch:
    """Tests for batch operations."""
    
    @pytest.fixture
    def client(self) -> Generator[MeilisearchClient, None, None]:
        """Create a test client with temporary index."""
        test_index = f"test_batch_{int(time.time())}"
        client = MeilisearchClient(index_name=test_index)
        yield client
        
        # Cleanup
        try:
            client.client.delete_index(test_index)
        except Exception:
            pass
    
    def test_add_documents_batch(self, client):
        """Test adding multiple documents in batch."""
        documents = [
            {
                "path": "/batch/doc1.pdf",
                "title": "Batch Doc 1",
                "content": "Content 1",
                "category": "test",
            },
            {
                "path": "/batch/doc2.pdf",
                "title": "Batch Doc 2",
                "content": "Content 2",
                "category": "test",
            },
            {
                "path": "/batch/doc3.pdf",
                "title": "Batch Doc 3",
                "content": "Content 3",
                "category": "test",
            },
        ]
        
        doc_ids = client.add_documents_batch(documents)
        
        assert len(doc_ids) == 3
        assert all(len(id) == 64 for id in doc_ids)
        
        # Wait for indexing
        time.sleep(1)
        
        # Verify all documents exist
        stats = client.get_stats()
        assert stats["total_documents"] == 3


class TestMeilisearchClientMocked:
    """Tests with mocked Meilisearch client."""
    
    @patch("search.meilisearch_client.Client")
    def test_health_check(self, mock_client_class):
        """Test health check with mocked client."""
        mock_client = MagicMock()
        mock_client.health.return_value = {"status": "available"}
        mock_client.get_index.return_value = MagicMock()
        mock_client_class.return_value = mock_client
        
        client = MeilisearchClient(index_name="test_mock")
        
        assert client.is_healthy() is True
        mock_client.health.assert_called()
