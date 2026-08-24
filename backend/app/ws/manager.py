import asyncio
import logging
from typing import Dict, Set
from fastapi import WebSocket
from app.core.worker import get_redis_pool

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections and Redis Pub/Sub subscriptions.
    Each event_id has its own set of connected clients and a single Redis listener task.
    """
    def __init__(self):
        # Maps event_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Maps event_id -> asyncio Task (Redis listener)
        self.listener_tasks: Dict[int, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, event_id: int):
        """
        Accepts a connection and starts a Redis listener for the event if not already running.
        """
        await websocket.accept()
        
        if event_id not in self.active_connections:
            self.active_connections[event_id] = set()
            # Start Redis listener for this event
            self.listener_tasks[event_id] = asyncio.create_task(
                self._redis_listener(event_id)
            )
            logger.info(f"Started Redis listener for event_updates_{event_id}")
            
        self.active_connections[event_id].add(websocket)
        logger.debug(f"Client connected to event {event_id}. Total: {len(self.active_connections[event_id])}")

    async def disconnect(self, websocket: WebSocket, event_id: int):
        """
        Removes a connection and stops the Redis listener if no clients remain.
        """
        if event_id in self.active_connections:
            self.active_connections[event_id].discard(websocket)
            logger.debug(f"Client disconnected from event {event_id}. Remaining: {len(self.active_connections[event_id])}")
            
            if not self.active_connections[event_id]:
                # No more clients, stop listener
                task = self.listener_tasks.pop(event_id, None)
                if task:
                    task.cancel()
                    logger.info(f"Stopped Redis listener for event_updates_{event_id}")
                self.active_connections.pop(event_id)

    async def _redis_listener(self, event_id: int):
        """
        Listens to a specific Redis channel and broadcasts messages to all event subscribers.
        """
        channel_name = f"event_updates_{event_id}"
        try:
            redis = await get_redis_pool()
            pubsub = redis.pubsub()
            await pubsub.subscribe(channel_name)
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    
                    await self._broadcast(event_id, data)
        except asyncio.CancelledError:
            # Task was cancelled due to no more subscribers
            pass
        except Exception as e:
            logger.error(f"Error in Redis listener for event {event_id}: {e}")
        finally:
            # Ensure cleanup if listener fails or stops
            if 'pubsub' in locals():
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()

    async def _broadcast(self, event_id: int, message: str):
        """
        Sends a message to all WebSocket clients subscribed to a specific event.
        """
        if event_id not in self.active_connections:
            return
            
        disconnected_clients = set()
        for connection in self.active_connections[event_id]:
            try:
                await connection.send_text(message)
            except Exception:
                # Client likely disconnected ungracefully
                disconnected_clients.add(connection)
        
        # Cleanup any dead connections found during broadcast
        for client in disconnected_clients:
            await self.disconnect(client, event_id)

manager = ConnectionManager()
