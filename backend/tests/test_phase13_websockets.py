import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.main import app
from app.models.user import User, UserRole
from app.models.event import Event
from app.models.inventory import ShowSeat, SeatStatus
from app.core.security import create_access_token
from app.services.publisher import seat_update_publisher
from app.ws.manager import manager

@pytest.fixture
def auth_token(db_session: Session):
    # Create a test user
    user = User(
        email="ws_test@example.com",
        hashed_password="...",
        full_name="WS Test User",
        role=UserRole.CUSTOMER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return create_access_token(subject=user.id)

@pytest.fixture
def test_event(db_session: Session):
    from app.models.venue import Venue, SeatCategory, Seat
    from app.models.event import EventCategoryPricing
    # Mock scheduler to avoid DB connection issues in background
    with patch("app.core.scheduler.start_scheduler", new_callable=AsyncMock):
        venue = Venue(name="WS Venue", address="WS City")
        db_session.add(venue)
        db_session.flush()
        
        category = SeatCategory(name="WS Cat")
        db_session.add(category)
        db_session.flush()
        
        seat = Seat(venue_id=venue.id, category_id=category.id, row_identifier="A", seat_number=1)
        db_session.add(seat)
        db_session.flush()
        
        event = Event(
            title="WS Event", 
            venue_id=venue.id, 
            organiser_id=1, 
            start_time=datetime.now() + timedelta(days=1)
        )
        db_session.add(event)
        db_session.flush()
        
        pricing = EventCategoryPricing(event_id=event.id, category_id=category.id, price=100.0)
        db_session.add(pricing)
        db_session.flush()
        
        show_seat = ShowSeat(event_id=event.id, physical_seat_id=seat.id, status=SeatStatus.AVAILABLE)
        db_session.add(show_seat)
        db_session.commit()
        db_session.refresh(show_seat)
        db_session.refresh(event)
        return event, show_seat

class TestPublisher:
    @pytest.mark.anyio
    async def test_publish_correct_format(self, mock_redis_pool):
        event_id = 1
        seat_id = 10
        status = "HELD"
        
        # Patching where it is used to be safe
        with patch("app.services.publisher.get_redis_pool", return_value=mock_redis_pool):
            await seat_update_publisher.publish_seat_status_update(event_id, seat_id, status)
        
        expected_channel = f"event_updates_{event_id}"
        expected_payload = json.dumps({"seat_id": seat_id, "new_status": status})
        
        mock_redis_pool.publish.assert_called_once_with(expected_channel, expected_payload)

    @pytest.mark.anyio
    async def test_publish_failure_handled(self, mock_redis_pool):
        mock_redis_pool.publish.side_effect = Exception("Redis Down")
        
        with patch("app.services.publisher.get_redis_pool", return_value=mock_redis_pool):
            # Should not raise exception
            await seat_update_publisher.publish_seat_status_update(1, 2, "BOOKED")
        
        assert mock_redis_pool.publish.called

class TestWebSocketAuth:
    def test_unauthenticated_ws_rejected(self, client: TestClient, test_event):
        event, _ = test_event
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/ws/events/{event.id}") as websocket:
                websocket.receive_text()

    def test_valid_token_ws_accepted(self, client: TestClient, test_event, auth_token):
        event, _ = test_event
        async def mock_connect(websocket, event_id):
            await websocket.accept()

        with patch("app.ws.manager.manager.connect", side_effect=mock_connect) as mock_connect_call:
            with client.websocket_connect(f"/api/v1/ws/events/{event.id}?token={auth_token}") as websocket:
                pass
            
            mock_connect_call.assert_called_once()

    def test_invalid_token_ws_rejected(self, client: TestClient, test_event):
        event, _ = test_event
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/ws/events/{event.id}?token=invalid") as websocket:
                websocket.receive_text()

class TestSubscriptionAndBroadcast:
    @pytest.mark.anyio
    async def test_broadcast_to_correct_event(self):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        event_id_1 = 1
        event_id_2 = 2
        
        manager.active_connections[event_id_1] = {ws1}
        manager.active_connections[event_id_2] = {ws2}
        
        message = json.dumps({"seat_id": 1, "new_status": "HELD"})
        await manager._broadcast(event_id_1, message)
        
        ws1.send_text.assert_called_once_with(message)
        ws2.send_text.assert_not_called()
        
        manager.active_connections.clear()

    @pytest.mark.anyio
    async def test_multiple_clients_same_event(self):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        event_id = 1
        
        manager.active_connections[event_id] = {ws1, ws2}
        message = "update"
        
        await manager._broadcast(event_id, message)
        
        ws1.send_text.assert_called_once_with(message)
        ws2.send_text.assert_called_once_with(message)
        
        manager.active_connections.clear()

class TestIntegration:
    def test_hold_creation_publishes(self, client: TestClient, db_session, test_event, auth_token):
        event, show_seat = test_event
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        with patch("app.services.publisher.seat_update_publisher.publish_seat_status_update") as mock_publish:
            response = client.post(f"/api/v1/holds", json={"show_seat_id": show_seat.id}, headers=headers)
            assert response.status_code == 201
            mock_publish.assert_called_once_with(event.id, show_seat.id, SeatStatus.HELD)

    def test_booking_confirmation_publishes(self, client: TestClient, db_session, test_event, auth_token):
        event, show_seat = test_event
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # 1. Hold the seat first
        client.post(f"/api/v1/holds", json={"show_seat_id": show_seat.id}, headers=headers)
        
        with patch("app.services.publisher.seat_update_publisher.publish_seat_status_update") as mock_publish:
            response = client.post("/api/v1/bookings/", json={"show_seat_ids": [show_seat.id]}, headers=headers)
            assert response.status_code == 201
            mock_publish.assert_called_once_with(event.id, show_seat.id, SeatStatus.BOOKED)

    def test_hold_release_publishes(self, client: TestClient, db_session, test_event, auth_token):
        event, show_seat = test_event
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # 1. Hold the seat first
        client.post(f"/api/v1/holds", json={"show_seat_id": show_seat.id}, headers=headers)
        
        with patch("app.services.publisher.seat_update_publisher.publish_seat_status_update") as mock_publish:
            response = client.delete(f"/api/v1/holds/{show_seat.id}", headers=headers)
            assert response.status_code == 200
            mock_publish.assert_called_once_with(event.id, show_seat.id, SeatStatus.AVAILABLE)

    def test_expired_hold_publishes(self, db_session, test_event):
        event, show_seat = test_event
        from app.services.hold import hold_service
        
        # Manually set to expired hold
        show_seat.status = SeatStatus.HELD
        show_seat.held_by_id = 1
        show_seat.hold_expires_at = datetime.now() - timedelta(minutes=1)
        db_session.add(show_seat)
        db_session.commit()
        
        with patch("app.services.publisher.seat_update_publisher.publish_seat_status_update") as mock_publish:
            hold_service.cleanup_expired_holds(db_session)
            mock_publish.assert_called_once_with(event.id, show_seat.id, SeatStatus.AVAILABLE)
