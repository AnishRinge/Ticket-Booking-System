import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.core.scheduler import cleanup_task, start_scheduler, stop_scheduler
from app.services.hold import hold_service
from app.services.waitlist import waitlist_service

@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_scheduler_cleanup_cycle_success(anyio_backend):
    """
    Verifies that the cleanup task correctly invokes the service-level cleanup methods.
    """
    with patch.object(hold_service, 'cleanup_expired_holds', return_value=5) as mock_hold_cleanup, \
         patch.object(waitlist_service, 'cleanup_expired_offers', return_value=3) as mock_waitlist_cleanup, \
         patch('app.core.scheduler.asyncio.sleep', side_effect=Exception("StopLoop")) as mock_sleep, \
         patch('app.core.scheduler.SessionLocal') as mock_session_local:
        
        # Setup mock DB session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        try:
            await cleanup_task()
        except Exception as e:
            if str(e) != "StopLoop":
                raise e
                
        # Verify both cleanup methods were called with a DB session
        mock_hold_cleanup.assert_called_once_with(mock_db)
        mock_waitlist_cleanup.assert_called_once_with(mock_db)
        
        # Verify session was closed
        mock_db.close.assert_called_once()

@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_scheduler_handles_exceptions_and_rolls_back(anyio_backend):
    """
    Verifies that the scheduler rolls back the session on error and continues.
    """
    with patch.object(hold_service, 'cleanup_expired_holds', side_effect=Exception("DB Error")) as mock_hold_cleanup, \
         patch('app.core.scheduler.asyncio.sleep', side_effect=Exception("StopLoop")) as mock_sleep, \
         patch('app.core.scheduler.SessionLocal') as mock_session_local:
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        try:
            await cleanup_task()
        except Exception as e:
            if str(e) != "StopLoop":
                raise e
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()
        # Verify session was closed regardless
        mock_db.close.assert_called_once()

@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_scheduler_lifecycle_full(anyio_backend):
    """
    Verifies the full lifecycle: start, duplicate start protection, stop, and restart.
    """
    # 1. Start scheduler
    await start_scheduler()
    import app.core.scheduler as scheduler_mod
    task1 = scheduler_mod._cleanup_task
    assert task1 is not None
    assert not task1.done()

    # 2. Repeated start should not change the task
    await start_scheduler()
    assert scheduler_mod._cleanup_task is task1

    # 3. Stop scheduler
    await stop_scheduler()
    assert scheduler_mod._cleanup_task is None
    assert task1.cancelled() or task1.done()

    # 4. Restart scheduler
    await start_scheduler()
    task2 = scheduler_mod._cleanup_task
    assert task2 is not None
    assert task2 is not task1
    
    # Cleanup for next tests
    await stop_scheduler()

@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_scheduler_startup_shutdown_integration(anyio_backend):
    """
    Verifies that the scheduler is correctly registered in FastAPI startup/shutdown.
    """
    from app.main import app as fastapi_app
    from fastapi.testclient import TestClient
    import app.core.scheduler as scheduler_mod
    
    # Ensure it's stopped
    await stop_scheduler()
    
    with TestClient(fastapi_app) as _:
        # After startup, it should be running
        assert scheduler_mod._cleanup_task is not None
        assert not scheduler_mod._cleanup_task.done()
        
    # After shutdown, it should be stopped
    assert scheduler_mod._cleanup_task is None
