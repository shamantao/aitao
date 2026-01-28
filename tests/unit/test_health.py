"""
Unit tests for health check module.

Tests the individual health check functions and overall status logic:
- check_service_lancedb
- check_service_meilisearch  
- check_service_worker
- check_health (overall status determination)
"""

import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Import schemas first
from src.api.schemas import ServiceStatus, HealthResponse

# Import the module to be tested so we can patch its imports
import src.api.routes.health as health_module


def run_async(coro):
    """Run async function synchronously for testing."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================================================
# Test check_service_lancedb
# ============================================================================

class TestCheckServiceLancedb:
    """Tests for LanceDB health check."""
    
    def test_lancedb_healthy(self):
        """Test LanceDB returns healthy when connected."""
        mock_client = MagicMock()
        mock_client.get_stats.return_value = {"total_documents": 100}
        
        with patch.object(health_module, "LanceDBClient", return_value=mock_client, create=True):
            # Force reimport of the function with patched import
            with patch.dict("sys.modules", {"src.search.lancedb_client": MagicMock(LanceDBClient=lambda: mock_client)}):
                result = run_async(health_module.check_service_lancedb())
                
                assert result.name == "lancedb"
                assert result.status == "healthy"
                assert "100 documents" in result.message
                assert result.latency_ms is not None
    
    def test_lancedb_down_on_exception(self):
        """Test LanceDB returns down when exception occurs."""
        with patch.dict("sys.modules", {"src.search.lancedb_client": MagicMock()}):
            with patch("src.search.lancedb_client.LanceDBClient", side_effect=Exception("Connection refused")):
                result = run_async(health_module.check_service_lancedb())
                
                assert result.name == "lancedb"
                assert result.status == "down"
    
    def test_lancedb_latency_measured(self):
        """Test that latency is measured for LanceDB check."""
        mock_client = MagicMock()
        mock_client.get_stats.return_value = {"total_documents": 50}
        
        with patch.dict("sys.modules", {"src.search.lancedb_client": MagicMock(LanceDBClient=lambda: mock_client)}):
            result = run_async(health_module.check_service_lancedb())
            
            assert result.latency_ms is not None
            assert result.latency_ms >= 0


# ============================================================================
# Test check_service_meilisearch
# ============================================================================

class TestCheckServiceMeilisearch:
    """Tests for Meilisearch health check."""
    
    def test_meilisearch_healthy(self):
        """Test Meilisearch returns healthy when connected."""
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.get_stats.return_value = {"numberOfDocuments": 200}
        
        with patch.dict("sys.modules", {"src.search.meilisearch_client": MagicMock(MeilisearchClient=lambda: mock_client)}):
            result = run_async(health_module.check_service_meilisearch())
            
            assert result.name == "meilisearch"
            assert result.status == "healthy"
            assert "200 documents" in result.message
    
    def test_meilisearch_down_when_not_connected(self):
        """Test Meilisearch returns down when not connected."""
        mock_client = MagicMock()
        mock_client.is_connected.return_value = False
        
        with patch.dict("sys.modules", {"src.search.meilisearch_client": MagicMock(MeilisearchClient=lambda: mock_client)}):
            result = run_async(health_module.check_service_meilisearch())
            
            assert result.name == "meilisearch"
            assert result.status == "down"
            assert "Not connected" in result.message
    
    def test_meilisearch_down_on_exception(self):
        """Test Meilisearch returns down when exception occurs."""
        def raise_exc():
            raise Exception("Server unavailable")
        
        with patch.dict("sys.modules", {"src.search.meilisearch_client": MagicMock(MeilisearchClient=raise_exc)}):
            result = run_async(health_module.check_service_meilisearch())
            
            assert result.name == "meilisearch"
            assert result.status == "down"


# ============================================================================
# Test check_service_worker
# ============================================================================

class TestCheckServiceWorker:
    """Tests for background worker health check."""
    
    def test_worker_healthy_when_running(self):
        """Test worker returns healthy when running."""
        mock_worker = MagicMock()
        mock_worker.is_running.return_value = True
        
        with patch.dict("sys.modules", {"src.indexation.worker": MagicMock(BackgroundWorker=lambda: mock_worker)}):
            result = run_async(health_module.check_service_worker())
            
            assert result.name == "worker"
            assert result.status == "healthy"
            assert "running" in result.message.lower()
    
    def test_worker_degraded_when_not_running(self):
        """Test worker returns degraded when not running."""
        mock_worker = MagicMock()
        mock_worker.is_running.return_value = False
        
        with patch.dict("sys.modules", {"src.indexation.worker": MagicMock(BackgroundWorker=lambda: mock_worker)}):
            result = run_async(health_module.check_service_worker())
            
            assert result.name == "worker"
            assert result.status == "degraded"
    
    def test_worker_degraded_on_exception(self):
        """Test worker returns degraded (not down) on exception."""
        def raise_exc():
            raise Exception("Worker import failed")
        
        with patch.dict("sys.modules", {"src.indexation.worker": MagicMock(BackgroundWorker=raise_exc)}):
            result = run_async(health_module.check_service_worker())
            
            assert result.name == "worker"
            assert result.status == "degraded"


# ============================================================================
# Test check_health (Overall Status Logic)
# ============================================================================

class TestCheckHealthOverall:
    """Tests for overall health status determination."""
    
    def _mock_services(self, lance_status, meili_status, worker_status):
        """Helper to create mock service status functions."""
        async def lance():
            return ServiceStatus(name="lancedb", status=lance_status, message="OK")
        async def meili():
            return ServiceStatus(name="meilisearch", status=meili_status, message="OK")
        async def worker():
            return ServiceStatus(name="worker", status=worker_status, message="OK")
        return lance, meili, worker
    
    def test_healthy_when_all_services_healthy(self):
        """Test overall status is healthy when all services up."""
        lance, meili, worker = self._mock_services("healthy", "healthy", "healthy")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            result = run_async(health_module.check_health(start_time=1000.0, version="2.2.15"))
            
            assert result.status == "healthy"
            assert result.version == "2.2.15"
    
    def test_degraded_when_one_service_down(self):
        """Test overall status is degraded when one search service down."""
        lance, meili, worker = self._mock_services("healthy", "down", "healthy")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            result = run_async(health_module.check_health(start_time=1000.0, version="2.2.15"))
            
            assert result.status == "degraded"
    
    def test_down_when_both_search_services_down(self):
        """Test overall status is down when both search backends fail."""
        lance, meili, worker = self._mock_services("down", "down", "healthy")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            result = run_async(health_module.check_health(start_time=1000.0, version="2.2.15"))
            
            # System is DOWN when both search backends unavailable
            assert result.status == "down"
    
    def test_degraded_when_worker_only_degraded(self):
        """Test overall is degraded when worker is degraded but search ok."""
        lance, meili, worker = self._mock_services("healthy", "healthy", "degraded")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            result = run_async(health_module.check_health(start_time=1000.0, version="2.2.15"))
            
            assert result.status == "degraded"
    
    def test_uptime_calculated_correctly(self):
        """Test uptime is calculated from start_time."""
        lance, meili, worker = self._mock_services("healthy", "healthy", "healthy")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            start = time.time() - 3600  # 1 hour ago
            result = run_async(health_module.check_health(start_time=start, version="2.2.15"))
            
            # Uptime should be approximately 3600 seconds
            assert result.uptime_seconds is not None
            assert 3599 <= result.uptime_seconds <= 3602
    
    def test_uptime_none_when_no_start_time(self):
        """Test uptime is None when start_time not provided."""
        lance, meili, worker = self._mock_services("healthy", "healthy", "healthy")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            result = run_async(health_module.check_health(start_time=None, version="2.2.15"))
            
            assert result.uptime_seconds is None
    
    def test_timestamp_is_present(self):
        """Test response includes current timestamp."""
        lance, meili, worker = self._mock_services("healthy", "healthy", "healthy")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            result = run_async(health_module.check_health(start_time=1000.0, version="2.2.15"))
            
            assert result.timestamp is not None
            assert isinstance(result.timestamp, datetime)
    
    def test_all_services_in_response(self):
        """Test all 4 services are included in response."""
        lance, meili, worker = self._mock_services("healthy", "healthy", "healthy")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            result = run_async(health_module.check_health(start_time=1000.0, version="2.2.15"))
            
            assert len(result.services) == 4
            assert "api" in result.services
            assert "lancedb" in result.services
            assert "meilisearch" in result.services
            assert "worker" in result.services
    
    def test_degraded_when_lancedb_only_down(self):
        """Test degraded when only LanceDB down (Meilisearch still up)."""
        lance, meili, worker = self._mock_services("down", "healthy", "healthy")
        
        with patch.object(health_module, "check_service_lancedb", side_effect=lance), \
             patch.object(health_module, "check_service_meilisearch", side_effect=meili), \
             patch.object(health_module, "check_service_worker", side_effect=worker):
            
            result = run_async(health_module.check_health(start_time=1000.0, version="2.2.15"))
            
            # Only one search service down = degraded (still functional)
            assert result.status == "degraded"


# ============================================================================
# Test ServiceStatus Schema
# ============================================================================

class TestServiceStatusSchema:
    """Tests for ServiceStatus Pydantic model."""
    
    def test_service_status_minimal(self):
        """Test ServiceStatus with minimal fields."""
        status = ServiceStatus(name="test", status="healthy", message="OK")
        
        assert status.name == "test"
        assert status.status == "healthy"
        assert status.message == "OK"
        assert status.latency_ms is None
    
    def test_service_status_with_latency(self):
        """Test ServiceStatus with latency."""
        status = ServiceStatus(
            name="test",
            status="healthy",
            message="OK",
            latency_ms=42.5
        )
        
        assert status.latency_ms == 42.5
    
    def test_service_status_valid_statuses(self):
        """Test ServiceStatus accepts valid status values."""
        for s in ["healthy", "degraded", "down"]:
            status = ServiceStatus(name="test", status=s, message="Test")
            assert status.status == s


# ============================================================================
# Test HealthResponse Schema
# ============================================================================

class TestHealthResponseSchema:
    """Tests for HealthResponse Pydantic model."""
    
    def test_health_response_structure(self):
        """Test HealthResponse has correct structure."""
        services = {
            "api": ServiceStatus(name="api", status="healthy", message="OK"),
            "lancedb": ServiceStatus(name="lancedb", status="healthy", message="OK"),
        }
        
        response = HealthResponse(
            status="healthy",
            version="2.2.15",
            timestamp=datetime.now(),
            services=services,
        )
        
        assert response.status == "healthy"
        assert response.version == "2.2.15"
        assert len(response.services) == 2
    
    def test_health_response_with_uptime(self):
        """Test HealthResponse with uptime."""
        services = {
            "api": ServiceStatus(name="api", status="healthy", message="OK"),
        }
        
        response = HealthResponse(
            status="healthy",
            version="2.2.15",
            timestamp=datetime.now(),
            services=services,
            uptime_seconds=3600.0,
        )
        
        assert response.uptime_seconds == 3600.0
