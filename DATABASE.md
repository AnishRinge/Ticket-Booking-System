# Database Design

## Overview
The Ticket Booking System uses PostgreSQL as the authoritative source of truth. The schema is designed to handle multiple venues, event-specific inventory, and concurrency-safe seat holds.

## Entities

### User & Authentication
* **users**: Stores user information and roles (CUSTOMER, ORGANISER, ADMIN).

### Venue & Seats
* **venues**: Physical locations for events.
* **seat_categories**: VIP, Premium, Standard, etc.
* **seats**: Physical seats tied to a venue and a category.

### Events & Pricing
* **events**: Specific shows/concerts.
* **event_category_pricings**: Per-event pricing for each seat category.

### Inventory
* **show_seats**: The core inventory table. Maps a physical seat to an event with a status (AVAILABLE, HELD, BOOKED).

### Bookings
* **bookings**: High-level booking records.
* **booking_seats**: Junction table linking bookings to specific show seats.

### Waitlist
* **waitlist_entries**: Users waiting for a specific category in an event.
* **waitlist_offers**: Time-limited offers sent to waitlisted users.

## Constraints
* **uq_show_seat_event_physical**: Unique constraint on `(event_id, physical_seat_id)` in `show_seats`.
* **Unique Emails**: Enforced on `users`.
* **Unique Booking Reference**: Enforced on `bookings`.

## Migration Instructions
The project uses PostgreSQL as the authoritative database in development and deployment.

The database is run through PostgreSQL 16. Alembic migrations are used to manage schema changes.

From backend/:

python -m alembic upgrade head

To create a new migration after a model change:

python -m alembic revision --autogenerate -m "description"

To verify the current migration:

python -m alembic current

## Verification
Model integrity and relationships have been verified using SQLite in-memory tests (`backend/tests/test_database.py`).
