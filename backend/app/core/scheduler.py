import asyncio
import logging
from typing import Optional
from app.db.session import SessionLocal
from app.services.hold import hold_service
from app.services.waitlist import waitlist_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Retention of task handle for lifecycle management
_cleanup_task: Optional[asyncio.Task] = None

async def cleanup_task():
    """
    Background task that periodically cleans up expired holds and waitlist offers.
    """
    try:
        while True:
            try:
                logger.info("Starting background cleanup cycle...")
                db = SessionLocal()
                try:
                    # 1. Cleanup expired holds
                    holds_cleaned = hold_service.cleanup_expired_holds(db)
                    if holds_cleaned > 0:
                        logger.info(f"Cleaned up {holds_cleaned} expired holds")

                    # 2. Cleanup expired waitlist offers
                    offers_cleaned = waitlist_service.cleanup_expired_offers(db)
                    if offers_cleaned > 0:
                        logger.info(f"Cleaned up {offers_cleaned} expired waitlist offers")
                    
                except Exception as e:
                    logger.error(f"Error during background cleanup cycle: {e}")
                    db.rollback()
                finally:
                    db.close()
                
                logger.info("Background cleanup cycle completed.")
            except Exception as e:
                logger.error(f"Unexpected error in background task loop: {e}")

            # Sleep for a configurable interval
            interval = settings.CLEANUP_INTERVAL_SECONDS
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("Background cleanup task received cancellation request.")
        # Perform any necessary cleanup here before exiting
        raise

async def start_scheduler():
    """
    Starts the background cleanup task if not already running.
    """
    global _cleanup_task
    if _cleanup_task is not None and not _cleanup_task.done():
        logger.warning("Background scheduler is already running.")
        return
    
    _cleanup_task = asyncio.create_task(cleanup_task())
    logger.info("Background scheduler started.")

async def stop_scheduler():
    """
    Stops the background cleanup task gracefully.
    """
    global _cleanup_task
    if _cleanup_task is None:
        logger.warning("Background scheduler is not running.")
        return

    logger.info("Stopping background scheduler...")
    _cleanup_task.cancel()
    try:
        await _cleanup_task
    except asyncio.CancelledError:
        pass
    finally:
        _cleanup_task = None
        logger.info("Background scheduler stopped and state reset.")
