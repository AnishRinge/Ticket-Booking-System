import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from arq.connections import RedisSettings
from app.core.config import settings
from app.core.worker import get_redis_pool, close_redis_pool
from app.worker.main import WorkerSettings, worker_test_task
from app.services.jobs import job_service

def test_worker_settings_configuration():
    """
    Verifies that WorkerSettings is correctly configured with settings.
    """
    assert WorkerSettings.redis_settings.host == settings.REDIS_HOST
    assert WorkerSettings.redis_settings.port == settings.REDIS_PORT
    assert WorkerSettings.redis_settings.database == settings.REDIS_DB
    assert worker_test_task in WorkerSettings.functions

@pytest.mark.anyio
async def test_redis_pool_lifecycle():
    """
    Verifies that the Redis pool can be initialized and closed.
    We mock arq.create_pool to avoid needing a real Redis.
    """
    with patch("app.core.worker.create_pool", new_callable=AsyncMock) as mock_create_pool:
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        try:
            pool = await get_redis_pool()
            assert pool == mock_pool
            mock_create_pool.assert_called_once()
        finally:
            await close_redis_pool()
            mock_pool.close.assert_called_once()

@pytest.mark.anyio
async def test_job_service_interface():
    """
    Verifies the job_service interface is correctly formed.
    """
    assert hasattr(job_service, "enqueue_test_job")
    
    with patch("app.services.jobs.get_redis_pool", new_callable=AsyncMock) as mock_get_pool:
        mock_pool = AsyncMock()
        mock_get_pool.return_value = mock_pool
        
        await job_service.enqueue_test_job("hello")
        
        mock_pool.enqueue_job.assert_called_once_with("worker_test_task", "hello")

def test_app_startup_import():
    """
    Verifies that the main app can still be imported without breaking.
    """
    from app.main import app
    assert app is not None
