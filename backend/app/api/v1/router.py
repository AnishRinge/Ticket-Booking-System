from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, auth, test_rbac, venues, events, holds, bookings, waitlist, ws, dashboard, users
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(test_rbac.router, prefix="/test", tags=["test"])
api_router.include_router(venues.router, prefix="/venues", tags=["venues"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(holds.router, prefix="/holds", tags=["holds"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(waitlist.router, prefix="/waitlist", tags=["waitlist"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

