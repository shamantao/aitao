"""
Unit tests for LanceDB client.

Tests vector database operations:
- Connection and initialization
- Document CRUD operations
- Semantic search
- Statistics and index management

OPTIMIZATION: Uses module-scoped embedding model to avoid reloading
the sentence-transformers model for each test class (~5s savings per class).
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import shutil

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from search.lancedb_client import LanceDBClient, LanceDBError


# =============================================================================
# MODULE-SCOPED FIXTURES (loaded once per test file)
# =============================================================================

@pytest.fixture(scope="module")
def shared_embedding_model():
    """
    Load embedding model once for all tests in this module.
    
    This is the key optimization: loading takes ~5s, doing it once
    instead of 6 times saves ~25-30 seconds.
    """
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def create_client_with_shared_model(temp_dir: str, shared_model) -> LanceDBClient:
    """Helper to create a LanceDB client with a shared embedding model."""
    client = LanceDBClient(
        db_path=temp_dir,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )
    # Inject the pre-loaded model to avoid reloading
    client.embedding_model = shared_model
    return client


class TestLanceDBClientInit:
    """Tests for LanceDBClient initialization."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary directory for test database."""
        temp_dir = tempfile.mkdtemp(prefix="lancedb_test_")
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_init_creates_database(self, temp_db_path):
        """Test that initialization creates the database directory."""
        db_path = Path(temp_db_path) / "test_db"
        
        # Use smaller model for tests
        client = LanceDBClient(
            db_path=str(db_path),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        assert db_path.exists()
        assert client.db is not None
        assert client.table_name == "aitao_embeddings"
    
    def test_init_with_custom_table_name(self, temp_db_path):
        """Test initialization with custom table name."""
        client = LanceDBClient(
            db_path=temp_db_path,
            table_name="custom_table",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        assert client.table_name == "custom_table"
        # list_tables() returns ListTablesResponse with .tables attribute
        tables = client.db.list_tables()
        table_names = tables.tables if hasattr(tables, 'tables') else list(tables)
        assert "custom_table" in table_names
    
    def test_init_sets_embedding_dimension(self, temp_db_path):
        """Test that embedding dimension is correctly detected."""
        client = LanceDBClient(
            db_path=temp_db_path,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # all-MiniLM-L6-v2 has 384 dimensions
        assert client.dimension == 384


class TestLanceDBClientCRUD:
    """Tests for document CRUD operations."""
    
    @pytest.fixture
    def client(self, shared_embedding_model):
        """Create a test client with temporary database using shared model."""
        temp_dir = tempfile.mkdtemp(prefix="lancedb_crud_")
        client = create_client_with_shared_model(temp_dir, shared_embedding_model)
        yield client
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
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
            metadata={"source": "test"}
        )
        
        assert doc_id is not None
        assert len(doc_id) == 64  # SHA256 hex
    
    def test_add_document_with_empty_content(self, client):
        """Test adding a document with empty content."""
        doc_id = client.add_document(
            path="/docs/empty.txt",
            title="Empty Document",
            content="",
        )
        
        # Should still work, with zero vector
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
        
        result = client.get_document(doc_id)
        
        assert result is not None
        assert result["id"] == doc_id
        assert result["path"] == path
        assert result["title"] == "Retrievable Doc"
        assert result["category"] == "test"
    
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
        
        # Verify it exists
        assert client.get_document(doc_id) is not None
        
        # Delete it
        result = client.delete(doc_id)
        assert result is True
        
        # Verify it's gone
        assert client.get_document(doc_id) is None
    
    def test_delete_nonexistent_document(self, client):
        """Test deleting a document that doesn't exist."""
        result = client.delete("nonexistent_" + "0" * 53)
        assert result is False
    
    def test_delete_by_path(self, client):
        """Test deleting a document by path."""
        path = "/docs/delete_by_path.pdf"
        client.add_document(
            path=path,
            title="Delete by Path",
            content="Content here.",
        )
        
        result = client.delete_by_path(path)
        assert result is True
        
        # Verify it's gone
        doc_id = client._generate_id(path)
        assert client.get_document(doc_id) is None
    
    def test_update_document(self, client):
        """Test that adding same path updates the document."""
        path = "/docs/update_me.pdf"
        
        # Add original
        doc_id1 = client.add_document(
            path=path,
            title="Original Title",
            content="Original content.",
        )
        
        # Add with same path (should update)
        doc_id2 = client.add_document(
            path=path,
            title="Updated Title",
            content="Updated content.",
        )
        
        # Same ID
        assert doc_id1 == doc_id2
        
        # Content should be updated
        result = client.get_document(doc_id1)
        assert result["title"] == "Updated Title"
        assert result["content"] == "Updated content."


class TestLanceDBClientSearch:
    """Tests for semantic search functionality."""
    
    @pytest.fixture
    def client_with_docs(self, shared_embedding_model):
        """Create client with sample documents using shared model."""
        temp_dir = tempfile.mkdtemp(prefix="lancedb_search_")
        client = create_client_with_shared_model(temp_dir, shared_embedding_model)
        
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
            content="Berlin is the capital of Germany. Visit the Brandenburg Gate and Museum Island.",
            category="travel",
            language="en",
        )
        
        yield client
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_search_returns_results(self, client_with_docs):
        """Test that search returns relevant results."""
        results = client_with_docs.search("France travel", limit=5)
        
        assert len(results) > 0
        assert all("_score" in r for r in results)
    
    def test_search_relevance(self, client_with_docs):
        """Test that most relevant results come first."""
        results = client_with_docs.search("programming Python", limit=3)
        
        # Python document should be most relevant
        assert results[0]["path"] == "/docs/tech/python.pdf"
    
    def test_search_with_category_filter(self, client_with_docs):
        """Test search with category filter."""
        results = client_with_docs.search(
            "capital city",
            limit=10,
            filter_category="travel"
        )
        
        # All results should be in travel category
        assert all(r["category"] == "travel" for r in results)
    
    def test_search_with_limit(self, client_with_docs):
        """Test search respects limit parameter."""
        results = client_with_docs.search("travel guide", limit=1)
        assert len(results) <= 1
    
    def test_search_empty_query(self, client_with_docs):
        """Test search with empty query returns results."""
        # Empty query should still return something (based on zero vector)
        results = client_with_docs.search("", limit=3)
        # May or may not return results depending on implementation
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
            assert "_score" in result
            assert "_distance" in result


class TestLanceDBClientStats:
    """Tests for statistics and index management."""
    
    @pytest.fixture
    def client(self, shared_embedding_model):
        """Create a test client using shared model."""
        temp_dir = tempfile.mkdtemp(prefix="lancedb_stats_")
        client = create_client_with_shared_model(temp_dir, shared_embedding_model)
        yield client
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_get_stats_empty_index(self, client):
        """Test statistics on empty index."""
        stats = client.get_stats()
        
        assert stats["total_documents"] == 0
        assert stats["categories"] == {}
        assert stats["languages"] == {}
        assert stats["total_size_bytes"] == 0
    
    def test_get_stats_with_documents(self, client):
        """Test statistics with documents."""
        # Add documents
        client.add_document(
            path="/doc1.pdf",
            title="Doc 1",
            content="Content 1",
            category="travel",
            language="en",
            file_size=1000,
        )
        client.add_document(
            path="/doc2.pdf",
            title="Doc 2",
            content="Content 2",
            category="travel",
            language="fr",
            file_size=2000,
        )
        client.add_document(
            path="/doc3.pdf",
            title="Doc 3",
            content="Content 3",
            category="tech",
            language="en",
            file_size=3000,
        )
        
        stats = client.get_stats()
        
        assert stats["total_documents"] == 3
        assert stats["categories"]["travel"] == 2
        assert stats["categories"]["tech"] == 1
        assert stats["languages"]["en"] == 2
        assert stats["languages"]["fr"] == 1
        assert stats["total_size_bytes"] == 6000
        assert stats["embedding_dimension"] == 384
    
    def test_clear_index(self, client):
        """Test clearing the index."""
        # Add documents
        client.add_document(path="/doc1.pdf", title="Doc 1", content="Content 1")
        client.add_document(path="/doc2.pdf", title="Doc 2", content="Content 2")
        
        # Verify they exist
        assert client.get_stats()["total_documents"] == 2
        
        # Clear
        count = client.clear()
        assert count == 2
        
        # Verify empty
        assert client.get_stats()["total_documents"] == 0


class TestLanceDBClientEmbedding:
    """Tests for embedding functionality."""
    
    @pytest.fixture
    def client(self, shared_embedding_model):
        """Create a test client using shared model."""
        temp_dir = tempfile.mkdtemp(prefix="lancedb_embed_")
        client = create_client_with_shared_model(temp_dir, shared_embedding_model)
        yield client
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_embed_text(self, client):
        """Test text embedding generation."""
        embedding = client._embed_text("This is a test sentence.")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
        assert all(isinstance(v, float) for v in embedding)
    
    def test_embed_empty_text(self, client):
        """Test embedding for empty text returns zero vector."""
        embedding = client._embed_text("")
        
        assert len(embedding) == 384
        assert all(v == 0.0 for v in embedding)
    
    def test_similar_texts_have_similar_embeddings(self, client):
        """Test that similar texts produce similar embeddings."""
        import numpy as np
        
        emb1 = client._embed_text("The quick brown fox jumps over the lazy dog.")
        emb2 = client._embed_text("A fast brown fox leaps over a sleepy dog.")
        emb3 = client._embed_text("Python is a programming language.")
        
        # Calculate cosine similarity
        def cosine_sim(a, b):
            a = np.array(a)
            b = np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        sim_12 = cosine_sim(emb1, emb2)  # Similar texts
        sim_13 = cosine_sim(emb1, emb3)  # Different texts
        
        # Similar texts should have higher similarity
        assert sim_12 > sim_13


class TestLanceDBClientMetadata:
    """Tests for metadata handling."""
    
    @pytest.fixture
    def client(self, shared_embedding_model):
        """Create a test client using shared model."""
        temp_dir = tempfile.mkdtemp(prefix="lancedb_meta_")
        client = create_client_with_shared_model(temp_dir, shared_embedding_model)
        yield client
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_add_with_metadata(self, client):
        """Test adding document with metadata."""
        metadata = {
            "author": "John Doe",
            "pages": 42,
            "tags": ["important", "reviewed"],
        }
        
        doc_id = client.add_document(
            path="/doc.pdf",
            title="Metadata Test",
            content="Content here",
            metadata=metadata,
        )
        
        result = client.get_document(doc_id)
        assert result["metadata"] == metadata
    
    def test_metadata_in_search_results(self, client):
        """Test that metadata is included in search results."""
        client.add_document(
            path="/doc.pdf",
            title="Search Metadata",
            content="Searchable content",
            metadata={"key": "value"},
        )
        
        results = client.search("Searchable content", limit=1)
        assert results[0]["metadata"] == {"key": "value"}
