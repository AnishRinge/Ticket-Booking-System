# TicketFlow — Event Ticket Booking System

TicketFlow is a full-stack event ticket booking platform built with **Next.js, FastAPI, PostgreSQL, Redis, and ARQ**.

The system supports customer booking, organiser event management, admin management, concurrency-safe seat inventory, temporary seat holds, FIFO waitlists, time-limited waitlist offers, real-time seat updates, QR ticket generation, and asynchronous notifications.

---

## Features

- JWT authentication with role-based access control
- Customer, Organiser, and Admin dashboards
- Event discovery and event management
- Interactive event seat maps
- Temporary seat holds with configurable TTL
- Concurrency-safe booking using PostgreSQL row-level locking
- Booking cancellation and seat release
- FIFO waitlist with automatic seat assignment
- Time-limited waitlist offers
- Redis Pub/Sub and WebSocket seat updates
- QR ticket generation
- Asynchronous booking confirmation emails
- Admin venue, layout, and user management
- Organiser event and revenue analytics

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL |
| Cache / Messaging | Redis |
| Background Jobs | ARQ |
| Authentication | JWT + Argon2 |
| Real-Time | WebSockets + Redis Pub/Sub |
| Migrations | Alembic |
| Deployment | Vercel + Backend Hosting Platform |

---

# Deployment

## Hosted Application

Frontend:

```text
https://ticketflow-rust-kappa.vercel.app
```

Backend API:

```text
https://ticketflow-backend-pxlv.onrender.com/
```

API documentation:

```text
https://ticketflow-backend-pxlv.onrender.com/docs
```

---

# Prerequisites

Install the following:

- Python 3.11+
- Node.js
- npm
- Docker Desktop
- Git

---

# Setup

## 1. Clone the Repository

```bash
git clone https://github.com/AnishRinge/Ticket-Booking-System
cd Ticket-Booking
```

---

## 2. Backend Setup

Create and activate a virtual environment:

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
cd backend
pip install -r requirements.txt
```

---

## 3. PostgreSQL

Start PostgreSQL using Docker:

```powershell
docker run --name ticket-booking-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=password `
  -e POSTGRES_DB=ticket_booking `
  -p 5432:5432 `
  -d postgres:16
```

---

## 4. Redis

Start Redis:

```powershell
docker run --name ticket-booking-redis `
  -p 6379:6379 `
  -d redis:7
```

---

## 5. Environment Variables

The backend environment template is provided at:

```text
backend/.env.example
```

Configure the required PostgreSQL, Redis, authentication, hold, waitlist, worker, and email settings.

Important configuration values include:

```text
DATABASE_URL
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB

REDIS_HOST
REDIS_PORT
REDIS_DB

SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES

SEAT_HOLD_TTL_SECONDS
WAITLIST_OFFER_TTL_SECONDS
CLEANUP_INTERVAL_SECONDS
```

The frontend uses:

```text
NEXT_PUBLIC_API_URL
```

For local development:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 6. Database Migration

From the `backend` directory:

```powershell
python -m alembic upgrade head
```

---

## 7. Start the Backend

```powershell
uvicorn app.main:app --reload --port 8000
```

Backend API:

```text
http://localhost:8000/api/v1
```

---

## 8. Start the ARQ Worker

The ARQ worker processes background jobs including:

- Booking confirmation
- QR ticket generation
- Waitlist offer notifications

The worker configuration is located at:

```text
backend/app/worker/main.py
```

Start the worker using the project's `WorkerSettings` configuration.

---

## 9. Frontend Setup

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:3000
```

---

# API Documentation

The backend provides interactive FastAPI OpenAPI documentation at:

```text
http://localhost:8000/docs
```

Main API groups include:

| API | Purpose |
|---|---|
| `/auth` | Registration, login, and authentication |
| `/events` | Event discovery and event management |
| `/holds` | Seat hold operations |
| `/bookings` | Booking, history, and cancellation |
| `/dashboard/organiser` | Organiser statistics and analytics |
| `/dashboard/admin` | Admin dashboard |
| `/users` | Admin user management |
| `/ws/events/{event_id}` | Real-time seat updates |

---

# Database Schema

PostgreSQL is the authoritative source of truth for users, events, inventory, bookings, and waitlists.

The main entities are:

```text
users
venues
seat_categories
seats
events
event_category_pricings
show_seats
bookings
booking_seats
waitlist_entries
waitlist_offers
```

The core inventory relationship is:

```text
Venue
  ↓
Physical Seats
  ↓
Event
  ↓
ShowSeats
  ↓
Bookings
  ↓
BookingSeats
```

The complete database design, relationships, constraints, and migration information are documented in:

```text
DATABASE.md
```

---

# Seat Hold and TTL Mechanism

When a customer selects a seat, the backend changes its event-specific `ShowSeat` state:

```text
AVAILABLE → HELD
```

The hold stores:

```text
held_by_id
hold_expires_at
```

The hold duration is controlled by:

```text
SEAT_HOLD_TTL_SECONDS
```

Before confirming a booking, the backend verifies:

1. The seat exists.
2. The seat is currently `HELD`.
3. The current user owns the hold.
4. The hold has not expired.
5. All requested seats belong to the same event.
6. Valid pricing exists.

After successful booking:

```text
HELD → BOOKED
```

Expired holds are automatically cleaned up by the background scheduler:

```text
HELD → AVAILABLE
```

The backend and database determine whether a hold is valid; the frontend countdown is only a user-interface representation.

---

# Concurrency Prevention

TicketFlow uses PostgreSQL row-level locking to prevent double booking.

Booking and seat-hold operations acquire locks using:

```sql
SELECT ... FOR UPDATE
```

Requested seat IDs are sorted before locking so multi-seat operations acquire locks in a deterministic order.

The booking transaction locks the requested seats and validates their state, hold ownership, expiration, event consistency, and pricing before creating the booking.

Only after all validations succeed are the booking and `BookingSeat` records created and the seats changed to:

```text
BOOKED
```

Because competing transactions cannot simultaneously modify the same locked inventory rows, two customers cannot successfully book the same seat.

---

# Waitlist Logic

Waitlists are maintained for a specific:

```text
Event + Seat Category
```

Customers enter the queue in FIFO order.

When a seat becomes available because of a cancellation or expired hold, the waitlist service identifies the first eligible customer and creates an offer.

The flow is:

```text
Seat Becomes Available
        ↓
Find First Eligible Waitlist Entry
        ↓
Create Waitlist Offer
        ↓
Notify Customer
        ↓
Customer Accepts / Offer Expires
        ↓
Accept → Booking
Expire → Continue Waitlist Processing
```

This allows released inventory to be automatically offered to waiting customers.

---

# Time-Limited Waitlist Offers

Each waitlist offer contains an explicit expiration timestamp.

The configured offer TTL is:

```text
WAITLIST_OFFER_TTL_SECONDS
```

The project's configured value is:

```text
900 seconds = 15 minutes
```

The expiration timestamp is stored by the backend.

A background scheduler periodically identifies expired offers and processes them so that inventory can continue through the waitlist.

The frontend timer does not determine offer validity.

---

# Real-Time Seat Updates

The initial seat map is retrieved through the REST API.

Seat changes are published through Redis Pub/Sub using event-specific channels:

```text
event_updates_{event_id}
```

Example payload:

```json
{
  "seat_id": 17,
  "new_status": "HELD"
}
```

The frontend receives these updates through the event-specific WebSocket endpoint:

```text
/ws/events/{event_id}
```

The matching seat is updated in the client seat map.

PostgreSQL remains the authoritative inventory source.

---

# Authentication and Roles

TicketFlow uses JWT authentication and Argon2 password hashing.

Supported roles:

### CUSTOMER

- Browse events
- View seat maps
- Hold seats
- Book seats
- View bookings
- Cancel bookings
- Join waitlists

### ORGANISER

- Create and manage events
- View owned events
- View booking statistics
- View revenue analytics
- Initialize event inventory

### ADMIN

- Manage venues
- Manage physical seat layouts
- View users
- Access administrative dashboards

Role-based authorization and ownership checks are enforced by the backend.

---

# Testing

Backend test suite:

```text
126 passed
```

Frontend production build:

```powershell
npm run build
```

Validation covers:

- Authentication
- Registration and login
- Role-based access control
- Event APIs
- Seat inventory
- Seat holds
- Booking confirmation
- Booking cancellation
- Waitlists
- Organiser dashboard
- Organiser events
- Organiser analytics
- Admin dashboard
- Admin venues
- Admin layouts
- Admin users
- PostgreSQL-backed API validation
- TypeScript validation
- WebSocket backend validation

---



# Project Documentation

Additional project documentation:

- `Architecture.md` — system architecture and design decisions
- `DATABASE.md` — database schema and relationships
- `SYSTEM_DESIGN.md` — evaluator-focused system design
- `backend/.env.example` — environment configuration template

---

# Submission Deliverables

The project submission contains:

1. README with setup instructions, environment configuration, API documentation, database schema, seat-hold logic, and waitlist logic
2. Hosted application URL
3. `SYSTEM_DESIGN.md` covering:
   - Seat hold and TTL mechanism
   - Concurrency prevention
   - Waitlist auto-assignment
   - Time-limited offer handling

---

# Project Structure

```text
Ticket-Booking/
│
├── backend/
│   ├── app/
│   ├── migrations/
│   ├── tests/
│   ├── alembic.ini
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── next.config.ts
│
├── Architecture.md
├── DATABASE.md
├── SYSTEM_DESIGN.md
└── README.md
```