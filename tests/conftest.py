"""
Shared pytest fixtures for AItao tests.

This module provides session-scoped fixtures to optimize test performance.
Key optimization: Embedding models are loaded once per test session,
not once per test class, reducing test time by ~70%.
"""

import pytest
import tempfile
import shutil
from pathlib import Path


# =============================================================================
# SESSION STARTUP MESSAGE
# =============================================================================

def pytest_configure(config):
    """Register custom markers and show startup message."""
    # Register markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m not slow')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_meilisearch: marks tests that need Meilisearch running"
    )


def pytest_sessionstart(session):
    """Show message at test session start."""
    print("\n" + "=" * 70)
    print("🧪 AItao Test Suite")
    print("=" * 70)
    print("⏱️  Estimated time: ~3-4 minutes")
    print("📦 Loading embedding model (sentence-transformers)...")
    print("   This is normal - the model loads once for all tests.")
    print("=" * 70 + "\n")


# =============================================================================
# LOGGER CLEANUP (Prevent test pollution)
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_loggers():
    """
    Clean up logger cache and handlers after each test.
    
    This prevents state pollution between tests that use get_logger().
    Without this, loggers accumulate handlers and the cache persists
    across tests, causing intermittent failures when run as a suite.
    """
    import logging
    
    yield  # Run the test
    
    # Clean up after test
    try:
        from src.core import logger as logger_module
        # Clear the module-level logger cache
        if hasattr(logger_module, '_loggers'):
            logger_module._loggers.clear()
    except ImportError:
        pass
    
    # Also clean up any test loggers from Python's logging
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith(('test_', 'cached_', 'module', 'fallback', 'indexer')):
            logger = logging.getLogger(name)
            logger.handlers.clear()


@pytest.fixture(scope="session")
def embedding_model():
    """
    Load the embedding model once for the entire test session.
    
    This is the main optimization: loading sentence-transformers takes ~5s,
    so loading it once instead of 6+ times saves significant time.
    """
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return model


@pytest.fixture(scope="session")
def embedding_dimension(embedding_model):
    """Get embedding dimension from the loaded model."""
    return embedding_model.get_sentence_embedding_dimension()


# =============================================================================
# LANCEDB FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def lancedb_temp_dir():
    """Create and cleanup a temporary directory for LanceDB tests."""
    temp_dir = tempfile.mkdtemp(prefix="lancedb_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def lancedb_client_with_shared_model(lancedb_temp_dir, embedding_model):
    """
    Create a LanceDB client that uses the shared embedding model.
    
    This avoids reloading the model for each test class.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    
    from search.lancedb_client import LanceDBClient
    
    # Create client with pre-loaded model
    client = LanceDBClient(
        db_path=lancedb_temp_dir,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )
    # Inject the shared model to avoid reloading
    client.embedding_model = embedding_model
    
    return client


# =============================================================================
# MEILISEARCH FIXTURES  
# =============================================================================

@pytest.fixture(scope="session")
def meilisearch_test_available():
    """Check if Meilisearch is available for integration tests."""
    try:
        import meilisearch
        client = meilisearch.Client("http://localhost:7700")
        client.health()
        return True
    except Exception:
        return False


# =============================================================================
# PATH FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def src_path(project_root):
    """Get the source code path."""
    return project_root / "src"


@pytest.fixture(scope="session")
def test_data_path(project_root):
    """Get the test data path (if exists)."""
    test_data = project_root / "tests" / "data"
    test_data.mkdir(exist_ok=True)
    return test_data


# =============================================================================
# MARKERS
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m not slow')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_meilisearch: marks tests that need Meilisearch running"
    )
