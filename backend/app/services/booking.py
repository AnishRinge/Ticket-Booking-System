from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import status

from app.models.booking import Booking, BookingSeat, BookingStatus
from app.models.inventory import ShowSeat, SeatStatus
from app.models.event import EventCategoryPricing
from app.models.user import User
from app.repositories.booking import booking_repository
from app.repositories.inventory import show_seat_repository
from app.repositories.event import event_pricing_repository
from app.core.exceptions import AppException

class BookingService:
    def confirm_booking(self, db: Session, show_seat_ids: List[int], user: User) -> Booking:
        if not show_seat_ids:
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="No seats provided for booking."
            )

        # Sort IDs to prevent deadlocks
        sorted_seat_ids = sorted(show_seat_ids)
        
        # Acquire locks on all requested seats in a deterministic order
        show_seats = (
            db.query(ShowSeat)
            .filter(ShowSeat.id.in_(sorted_seat_ids))
            .order_by(ShowSeat.id)
            .with_for_update()
            .all()
        )

        if len(show_seats) != len(show_seat_ids):
            db.rollback()
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="One or more seats not found."
            )

        now = datetime.now()
        event_id = show_seats[0].event_id
        total_price = 0.0
        booking_seats_data = []

        for seat in show_seats:
            # 1. Status check
            if seat.status != SeatStatus.HELD:
                db.rollback()
                raise AppException(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Seat {seat.id} is not in HELD state."
                )

            # 2. Ownership check
            if seat.held_by_id != user.id:
                db.rollback()
                raise AppException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=f"Seat {seat.id} is not held by you."
                )

            # 3. Expiration check
            if seat.hold_expires_at <= now:
                db.rollback()
                # Optionally reconcile state here, but the background worker or next hold attempt will do it.
                # For now, just reject the booking.
                raise AppException(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Hold for seat {seat.id} has expired."
                )
            
            # 4. Consistency check (all seats must belong to the same event)
            if seat.event_id != event_id:
                db.rollback()
                raise AppException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="All seats must belong to the same event."
                )

            # 5. Price lookup
            pricing = event_pricing_repository.get_by_event_and_category(
                db, event_id=event_id, category_id=seat.physical_seat.category_id
            )
            if not pricing:
                db.rollback()
                raise AppException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pricing not found for seat {seat.id} category."
                )
            
            price = pricing.price
            total_price += price
            booking_seats_data.append((seat, price))

        # Create Booking
        booking = Booking(
            user_id=user.id,
            event_id=event_id,
            status=BookingStatus.CONFIRMED,
            total_price=total_price
        )
        db.add(booking)
        db.flush() # Get booking.id

        # Create BookingSeats and update ShowSeats
        for seat, price in booking_seats_data:
            booking_seat = BookingSeat(
                booking_id=booking.id,
                show_seat_id=seat.id,
                price_at_booking=price
            )
            db.add(booking_seat)
            
            # Update ShowSeat status
            seat.status = SeatStatus.BOOKED
            seat.held_by_id = None
            seat.hold_expires_at = None
            db.add(seat)

        try:
            db.commit()
            db.refresh(booking)
            
            # Integration: Trigger fulfillment (QR + Email)
            from app.services.notification import notification_service
            notification_service.send_booking_confirmation_sync(booking.id)

            return booking
        except Exception as e:
            db.rollback()
            raise AppException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to confirm booking: {str(e)}"
            )

    def cancel_booking(self, db: Session, booking_id: int, user: User) -> Booking:
        booking = (
            db.query(Booking)
            .filter(Booking.id == booking_id)
            .with_for_update()
            .first()
        )

        if not booking:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found."
            )

        if booking.user_id != user.id:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not own this booking."
            )

        if booking.status == BookingStatus.CANCELLED:
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Booking is already cancelled."
            )

        # Update Booking status
        booking.status = BookingStatus.CANCELLED
        db.add(booking)

        # Release seats
        booking_seats = (
            db.query(BookingSeat)
            .filter(BookingSeat.booking_id == booking.id)
            .all()
        )
        
        seat_ids = [bs.show_seat_id for bs in booking_seats]
        sorted_seat_ids = sorted(seat_ids)
        
        # Acquire locks on all requested seats in a deterministic order
        show_seats = (
            db.query(ShowSeat)
            .filter(ShowSeat.id.in_(sorted_seat_ids))
            .order_by(ShowSeat.id)
            .with_for_update()
            .all()
        )

        for seat in show_seats:
            seat.status = SeatStatus.AVAILABLE
            seat.held_by_id = None
            seat.hold_expires_at = None
            db.add(seat)

        # Integration: Trigger waitlist allocation for released seats
        from app.services.waitlist import waitlist_service
        for seat in show_seats:
            waitlist_service.process_waitlist_for_seat(db, show_seat_id=seat.id, commit=False)

        try:
            db.commit()
            db.refresh(booking)
            return booking
        except Exception as e:
            db.rollback()
            raise AppException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to cancel booking: {str(e)}"
            )

    def get_booking(self, db: Session, booking_id: int, user: User) -> Booking:
        booking = booking_repository.get_with_details(db, booking_id=booking_id)
        if not booking:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Booking not found."
            )
        
        if booking.user_id != user.id:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not own this booking."
            )
        
        return booking

    def get_user_bookings(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Booking], int]:
        bookings = booking_repository.get_by_user(db, user_id=user_id, skip=skip, limit=limit)
        total = booking_repository.get_count_by_user(db, user_id=user_id)
        return bookings, total

booking_service = BookingService()
