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
Since a live PostgreSQL instance was not available during development, migrations must be generated and applied once a database is accessible.

1. Ensure `.env` is configured with correct `POSTGRES_*` values.
2. Run the following command from the `backend` directory to generate the initial migration:
   ```bash
   python -m alembic revision --autogenerate -m "Initial migration"
   ```
3. Apply the migration:
   ```bash
   python -m alembic upgrade head
   ```

## Verification
Model integrity and relationships have been verified using SQLite in-memory tests (`backend/tests/test_database.py`).
