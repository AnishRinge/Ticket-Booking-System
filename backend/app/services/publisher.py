import json
import logging
from app.core.worker import get_redis_pool

logger = logging.getLogger(__name__)

class SeatUpdatePublisher:
    """
    Handles publishing seat status updates to Redis Pub/Sub.
    """
    
    async def publish_seat_status_update(self, event_id: int, seat_id: int, new_status: str):
        """
        Publishes a minimal JSON payload to the event-scoped Redis channel.
        Payload: {"seat_id": <int>, "new_status": "<status>"}
        Channel: event_updates_{event_id}
        """
        try:
            channel = f"event_updates_{event_id}"
            payload = {
                "seat_id": seat_id,
                "new_status": new_status
            }
            message = json.dumps(payload)
            
            redis = await get_redis_pool()
            await redis.publish(channel, message)
            
            logger.debug(f"Published update to {channel}: {message}")
        except Exception as e:
            # Redis failure should NOT roll back the database transaction.
            # We log it and continue.
            logger.error(f"Failed to publish seat status update to Redis: {e}")

    def publish_seat_status_update_sync(self, event_id: int, seat_id: int, new_status: str):
        """
        Sync bridge for publishing seat status updates.
        Ensures failures don't impact the business transaction.
        """
        import asyncio
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We are in an async context (FastAPI)
                loop.create_task(self.publish_seat_status_update(event_id, seat_id, new_status))
            else:
                # We are in a sync context (tests/CLI)
                asyncio.run(self.publish_seat_status_update(event_id, seat_id, new_status))
        except Exception as e:
            logger.error(f"Failed to trigger sync seat status update: {e}")

seat_update_publisher = SeatUpdatePublisher()
