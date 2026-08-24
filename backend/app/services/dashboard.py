from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.event import Event
from app.models.booking import Booking, BookingStatus
from app.models.user import User, UserRole
from app.models.venue import Venue

class DashboardService:
    def get_organiser_dashboard(self, db: Session, organiser_id: int):
        # Total events by this organiser
        events_query = db.query(Event).filter(Event.organiser_id == organiser_id)
        total_events = events_query.count()

        # Total bookings and revenue for events by this organiser
        bookings = (
            db.query(Booking)
            .join(Event)
            .filter(Event.organiser_id == organiser_id, Booking.status == BookingStatus.CONFIRMED)
            .all()
        )
        total_bookings = len(bookings)
        total_revenue = sum(b.total_price for b in bookings)

        # Recent events with summaries
        recent_events = []
        for event in events_query.order_by(Event.start_time.desc()).limit(5).all():
            event_bookings = [b for b in event.bookings if b.status == BookingStatus.CONFIRMED]
            recent_events.append({
                "id": event.id,
                "title": event.title,
                "bookings_count": len(event_bookings),
                "revenue": float(sum(b.total_price for b in event_bookings)),
                "start_time": event.start_time.isoformat(),
                "status": "Upcoming" if event.start_time > datetime.now() else "Completed"
            })

        return {
            "total_events": total_events,
            "total_bookings": total_bookings,
            "total_revenue": float(total_revenue),
            "recent_events": recent_events
        }

    def get_admin_dashboard(self, db: Session):
        total_venues = db.query(Venue).count()
        total_events = db.query(Event).count()
        
        confirmed_bookings = db.query(Booking).filter(Booking.status == BookingStatus.CONFIRMED).all()
        total_revenue = sum(b.total_price for b in confirmed_bookings)
        
        total_users = db.query(User).count()

        recent_bookings = []
        for b in db.query(Booking).order_by(Booking.created_at.desc()).limit(10).all():
            recent_bookings.append({
                "id": b.id,
                "reference": b.booking_reference,
                "user_email": b.user.email,
                "event_title": b.event.title,
                "status": b.status,
                "total_price": float(b.total_price),
                "created_at": b.created_at.isoformat()
            })

        return {
            "total_venues": total_venues,
            "total_events": total_events,
            "total_revenue": float(total_revenue),
            "total_users": total_users,
            "recent_bookings": recent_bookings
        }

dashboard_service = DashboardService()
