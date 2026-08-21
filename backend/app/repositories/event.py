from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.event import Event, EventCategoryPricing
from app.repositories.base import BaseRepository

class EventRepository(BaseRepository[Event]):
    def get_by_organiser(
        self, db: Session, *, organiser_id: int, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        return (
            db.query(self.model)
            .filter(self.model.organiser_id == organiser_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_events(
        self,
        db: Session,
        *,
        title: Optional[str] = None,
        venue_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        query = db.query(self.model)
        if title:
            query = query.filter(self.model.title.ilike(f"%{title}%"))
        if venue_id:
            query = query.filter(self.model.venue_id == venue_id)
        return query.offset(skip).limit(limit).all()

class EventCategoryPricingRepository(BaseRepository[EventCategoryPricing]):
    def get_by_event(self, db: Session, *, event_id: int) -> List[EventCategoryPricing]:
        return db.query(self.model).filter(self.model.event_id == event_id).all()

    def get_by_event_and_category(
        self, db: Session, *, event_id: int, category_id: int
    ) -> Optional[EventCategoryPricing]:
        return (
            db.query(self.model)
            .filter(
                self.model.event_id == event_id,
                self.model.category_id == category_id
            )
            .first()
        )

event_repository = EventRepository(Event)
event_pricing_repository = EventCategoryPricingRepository(EventCategoryPricing)
