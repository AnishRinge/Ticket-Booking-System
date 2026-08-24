import logging
import jwt
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.repositories.user import user_repository
from app.repositories.event import event_repository
from app.schemas.auth import TokenPayload
from app.ws.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_current_user_ws(
    websocket: WebSocket,
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None)
) -> Optional[int]:
    """
    Authenticates a WebSocket connection using a JWT token from query parameters.
    Returns the user_id if successful, otherwise closes the connection.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
        
    try:
        payload = decode_token(token)
        token_data = TokenPayload(**payload)
        user_id = token_data.sub
        
        user = user_repository.get(db, id=user_id)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
            
        return user_id
    except (jwt.PyJWTError, Exception):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

@router.websocket("/events/{event_id}")
async def event_updates(
    websocket: WebSocket,
    event_id: int,
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time seat status updates.
    Requires authentication via token query parameter.
    """
    # 1. Authenticate
    user_id = await get_current_user_ws(websocket, db, token)
    if not user_id:
        return

    # 2. Validate Event exists
    event = event_repository.get(db, id=event_id)
    if not event:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return

    # 3. Connect and manage life-cycle
    await manager.connect(websocket, event_id)
    try:
        while True:
            # Keep connection alive and wait for client to close it
            # We don't expect messages from client for now, but we must receive to detect disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, event_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id} on event {event_id}: {e}")
        await manager.disconnect(websocket, event_id)
