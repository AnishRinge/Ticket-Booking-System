# TicketFlow — Event Ticket Booking System

TicketFlow is a full-stack event ticket booking platform designed around concurrency-safe seat inventory, temporary seat holds, transactional bookings, FIFO waitlists, real-time seat updates, QR-code tickets, and role-based dashboards.

The system supports three roles:

- **Customer** — browse events, select seats, hold and book tickets, manage bookings, and join waitlists.
- **Organiser** — create/manage events and view booking and revenue analytics.
- **Admin** — manage venues, physical seat layouts, and users.

---

## Features

### Customer

- User registration and authentication
- JWT-based login
- Browse and filter events
- View event details
- Visual seat map
- Seat categories and event-specific pricing
- Temporary seat holds
- Automatic expiration of holds
- Concurrency-safe booking
- Booking confirmation
- Booking history
- Booking details and ticket information
- Booking cancellation
- FIFO waitlists
- Time-limited waitlist offers
- QR-code ticket generation
- Email booking confirmations
- Real-time seat status updates

### Organiser

- Organiser authentication
- Organiser dashboard
- Create and manage events
- View managed events
- Event details
- Booking statistics
- Revenue statistics
- Analytics dashboard

### Admin

- Admin authentication
- System dashboard
- Venue management
- Physical seat layout management
- User management
- Role-based access control

---

# Architecture

```text
                         ┌─────────────────────┐
                         │   Next.js Frontend  │
                         │                     │
                         │ Customer / Organiser│
                         │ Admin Dashboards    │
                         └──────────┬──────────┘
                                    │
                              REST / WebSocket
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   FastAPI Backend   │
                         │                     │
                         │ API / RBAC / Logic  │
                         │ Transactions        │
                         └───────┬─────┬───────┘
                                 │     │
                    ┌────────────┘     └─────────────┐
                    ▼                                ▼
          ┌──────────────────┐              ┌──────────────────┐
          │   PostgreSQL     │              │      Redis       │
          │                  │              │                  │
          │ Source of Truth  │              │ Queue / PubSub   │
          └──────────────────┘              └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │    ARQ Worker    │
                                            │                  │
                                            │ QR Generation    │
                                            │ Email Delivery   │
                                            └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │  Email Provider  │
                                            └──────────────────┘

## Main Components

### Next.js Frontend

Provides the customer, organiser, and admin interfaces.

The frontend contains:

- Public event discovery
- Event details
- Interactive seat selection
- Booking flow
- Booking history
- Ticket details
- Customer dashboard
- Organiser dashboard
- Organiser event management
- Organiser analytics
- Admin dashboard
- Venue management
- Physical seat layout management
- User management

### FastAPI Backend

Provides:

- REST APIs
- Authentication
- JWT token handling
- Role-based access control
- Event management
- Inventory management
- Seat holds
- Booking transactions
- Booking cancellation
- Waitlist management
- Dashboard APIs
- WebSocket endpoints

### PostgreSQL

PostgreSQL is the authoritative source of truth for:

- Users
- Venues
- Physical seats
- Seat categories
- Events
- Event pricing
- Event-specific seat inventory
- Bookings
- Booking seats
- Waitlist entries
- Waitlist offers

### Redis

Redis provides:

- Background job queue infrastructure
- Redis Pub/Sub for real-time seat updates

### ARQ Worker

The ARQ worker processes asynchronous jobs including:

- Booking confirmation emails
- QR ticket generation
- Waitlist offer emails

### Background Scheduler

The background scheduler periodically processes:

- Expired seat holds
- Expired waitlist offers

### WebSockets

WebSockets provide event-specific real-time seat status updates.

---

# Technology Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- Axios
- Recharts
- Lucide React

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Alembic
- JWT authentication
- Argon2 password hashing

## Infrastructure

- PostgreSQL 16
- Redis 7
- ARQ
- Docker
- Redis Pub/Sub
- WebSockets

---

# Repository Structure

```text
Ticket-Booking/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       └── router.py
│   │   │
│   │   ├── core/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── worker/
│   │   └── ws/
│   │
│   ├── migrations/
│   ├── tests/
│   ├── alembic.ini
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── types/
│   ├── package.json
│   └── next.config.ts
│
├── Architecture.md
├── DATABASE.md
└── README.md

# Prerequisites

Install:

- Python 3.11+
- Node.js
- npm
- Docker Desktop

Docker is used to run PostgreSQL and Redis locally.

---

# Local Setup

## 1. Clone the Repository

```bash
git clone <repository-url>
cd Ticket-Booking
```

---

# Backend Setup

## 2. Create Virtual Environment

From the project root:

### Windows PowerShell

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3. Install Backend Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

---

# PostgreSQL

Start PostgreSQL using Docker:

```powershell
docker run --name ticket-booking-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=password `
  -e POSTGRES_DB=ticket_booking `
  -p 5432:5432 `
  -d postgres:16
```

Verify:

```powershell
docker ps
```

PostgreSQL should be available at:

```text
localhost:5432
```

---

# Redis

Start Redis using Docker:

```powershell
docker run --name ticket-booking-redis `
  -p 6379:6379 `
  -d redis:7
```

Verify:

```powershell
docker ps
```

Redis should be available at:

```text
localhost:6379
```

---

# Environment Variables

Configure the backend using the project's environment configuration.

The configuration includes:

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

SMTP / email provider configuration
```

Never commit real credentials, API keys, passwords, or secret keys.

The frontend uses:

```text
NEXT_PUBLIC_API_URL
```

For local development:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

# Database Migrations

From the `backend` directory:

```powershell
python -m alembic upgrade head
```

Check the current migration:

```powershell
python -m alembic current
```

To create a new migration after a model change:

```powershell
python -m alembic revision --autogenerate -m "description"
```

---

# Start FastAPI

From:

```text
Ticket-Booking/backend
```

run:

```powershell
uvicorn app.main:app --reload --port 8000
```

API base URL:

```text
http://localhost:8000/api/v1
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

---

# Start ARQ Worker

The ARQ worker processes:

- Booking confirmation emails
- QR ticket generation
- Waitlist offer notifications

The worker configuration is defined in:

```text
backend/app/worker/main.py
```

Start the ARQ worker using the `WorkerSettings` configuration defined in that file.

---

# Frontend Setup

Open another terminal.

From the project root:

```powershell
cd frontend
npm install
```

Start the development server:

```powershell
npm run dev
```

The frontend runs on:

```text
http://localhost:3000
```

---

# Production Build

Build the frontend:

```powershell
npm run build
```

---

# Authentication and RBAC

TicketFlow uses JWT-based authentication.

Passwords are securely hashed using Argon2.

Supported roles:

```text
CUSTOMER
ORGANISER
ADMIN
```

Access is enforced through FastAPI dependencies and ownership checks.

## Customer

Customers can:

- Browse events
- View seat maps
- Hold seats
- Book seats
- View their own bookings
- Cancel their own bookings
- Join waitlists
- Complete booking flows

## Organiser

Organisers can:

- Create events
- Manage owned events
- View organiser events
- View booking statistics
- View revenue analytics

## Admin

Administrators can:

- Manage venues
- Manage physical layouts
- View users
- Access administrative dashboards

---

# Seat Inventory Model

The system separates physical seats from event-specific inventory.

```text
Venue
  │
  └── Physical Seat
          │
          ├── Event A → ShowSeat
          │
          └── Event B → ShowSeat
```

A physical seat belongs permanently to a venue.

A `ShowSeat` represents the state of that physical seat for a particular event.

This allows the same venue and physical seating layout to be reused across multiple events.

---

# Seat State Machine

```text
AVAILABLE
    │
    │ Hold
    ▼
  HELD
   │  │
   │  └─────────────── TTL expiry ────────────┐
   │                                           │
   │ Booking                                  ▼
   ▼                                      AVAILABLE
 BOOKED
   │
   │ Cancellation
   ▼
AVAILABLE
```

---

# Seat Holds

Seat holds are temporary reservations.

When a customer requests a seat:

```text
AVAILABLE → HELD
```

The backend stores:

```text
held_by_id
hold_expires_at
```

The hold TTL is configurable.

The backend is authoritative. Client-side countdowns do not determine whether a hold is valid.

When the TTL expires, the scheduler releases the seat:

```text
HELD → AVAILABLE
```

Released inventory can then trigger waitlist processing.

---

# Concurrency Protection

TicketFlow uses PostgreSQL row-level locking to prevent race conditions.

Booking and hold operations use:

```sql
SELECT ...
FOR UPDATE
```

The requested seat IDs are sorted before locking.

This ensures that:

- Concurrent transactions cannot both modify the same seat
- Only one customer can successfully acquire a seat
- Multi-seat operations acquire locks deterministically
- Database transactions remain atomic

PostgreSQL is therefore the authoritative source of truth for inventory state.

---

# Booking Flow

```text
Customer
   │
   ▼
Select Seats
   │
   ▼
Create Hold
   │
   ▼
HELD
   │
   ▼
Confirm Booking
   │
   ├── Validate ownership
   ├── Validate TTL
   ├── Validate pricing
   ├── Create Booking
   ├── Create BookingSeat records
   └── Change ShowSeat → BOOKED
          │
          ▼
   Background Fulfillment
          │
          ├── Generate QR
          └── Send Email
```

---

# Cancellation

A customer can cancel their own confirmed booking.

The cancellation transaction:

1. Locks the booking.
2. Validates ownership.
3. Changes booking status to `CANCELLED`.
4. Locks the associated seats.
5. Changes seats to `AVAILABLE`.
6. Processes eligible waitlist customers.
7. Publishes seat-status updates.

---

# Waitlist

Waitlists are scoped to:

```text
Event + Seat Category
```

Customers join a FIFO queue.

The queue is ordered by creation time.

When inventory becomes available:

```text
Seat Released
      │
      ▼
Find First Eligible Waitlist Entry
      │
      ▼
Create Waitlist Offer
      │
      ▼
15-Minute Offer Window
      │
      ├── Accept → Booking
      │
      └── Expire/Decline → Next Customer
```

The configured offer TTL is:

```text
900 seconds = 15 minutes
```

The scheduler automatically processes expired offers.

---

# Real-Time Seat Updates

The initial seat map is retrieved through the REST API.

Seat-state changes are published to Redis Pub/Sub.

Event-specific channels use:

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

The WebSocket endpoint provides event-scoped updates to connected clients.

The frontend applies the update directly to the matching `ShowSeat`.

REST and PostgreSQL remain authoritative for inventory state.

---

# QR Tickets

After booking confirmation, an asynchronous ARQ job is created.

The worker:

1. Loads the booking.
2. Builds a ticket payload.
3. Generates a QR code.
4. Produces a PNG image.
5. Creates the booking confirmation email.
6. Attaches the QR PNG.
7. Sends the email to the customer.

The QR payload contains booking and seat information needed to identify the ticket.

---

# Email Notifications

Booking confirmation emails include:

- Event
- Date/time
- Venue
- Booking reference
- Seats
- Total price
- QR ticket attachment

Waitlist offer emails include:

- Event
- Venue
- Seat category
- Offer expiration time

Email delivery is handled asynchronously through the background worker.

Failed background jobs are retried according to the worker configuration.

---

# API Overview

| Domain | Endpoint | Access |
|---|---|---|
| Authentication | `POST /auth/register` | Public |
| Authentication | `POST /auth/login` | Public |
| Authentication | `GET /auth/me` | Authenticated |
| Events | `GET /events` | Public |
| Events | `GET /events/{event_id}` | Public |
| Events | `POST /events` | Organiser |
| Events | `PATCH /events/{event_id}` | Organiser |
| Events | `DELETE /events/{event_id}` | Organiser |
| Inventory | `GET /events/{event_id}/seat-map` | Public |
| Inventory | `POST /events/{event_id}/inventory/initialize` | Organiser/Admin |
| Holds | `POST /holds` | Authenticated |
| Holds | `DELETE /holds/{show_seat_id}` | Authenticated |
| Holds | `GET /holds` | Authenticated |
| Bookings | `POST /bookings` | Authenticated |
| Bookings | `GET /bookings` | Authenticated |
| Bookings | `GET /bookings/{booking_id}` | Authenticated |
| Bookings | `POST /bookings/{booking_id}/cancel` | Authenticated |
| Waitlist | `POST /events/{event_id}/waitlist` | Customer |
| Dashboard | `GET /dashboard/organiser` | Organiser |
| Dashboard | `GET /dashboard/admin` | Admin |
| Users | `GET /users` | Admin |
| WebSocket | `/ws/events/{event_id}` | Authenticated |

Complete request and response schemas are available through the FastAPI OpenAPI documentation.

---

# Testing

The backend test suite currently reports:

```text
126 passed
```

The frontend production build passes successfully using:

```powershell
npm run build
```

Validation covers:

- Authentication
- Registration
- Login
- Role-based access control
- Event APIs
- Seat inventory
- Seat holds
- Booking confirmation
- Booking cancellation
- Waitlist functionality
- Organiser dashboard
- Organiser event management
- Organiser analytics
- Admin dashboard
- Admin venue management
- Admin layout management
- Admin user management
- TypeScript validation
- PostgreSQL-backed API verification
- WebSocket backend handshake verification

---

# Database

See `DATABASE.md` for the detailed database design.

The main inventory relationship is:

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

Waitlist data is represented by:

```text
WaitlistEntry
        ↓
WaitlistOffer
```

---

# Architecture Documentation

See `Architecture.md` for:

- System architecture
- Actors and RBAC
- Domain model
- Seat state machine
- Hold architecture
- Concurrency strategy
- Waitlist architecture
- Booking flow
- Real-time architecture
- Security architecture
- Transactional correctness
- Failure handling
- Architectural decisions

---

# Security

Security mechanisms include:

- Argon2 password hashing
- JWT authentication
- Role-based authorization
- Ownership validation
- Pydantic request validation
- PostgreSQL transactions
- Row-level locking
- Environment-based secrets
- Sanitized administrative user responses

Password hashes are never returned through the user management API.

---

# Development Commands

## Backend Tests

```powershell
cd backend
python -m pytest tests -q
```

## Backend Server

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

## Frontend Development

```powershell
cd frontend
npm run dev
```

## Frontend Production Build

```powershell
cd frontend
npm run build
```

## Database Migrations

```powershell
cd backend
python -m alembic upgrade head
```

---

# Project Evaluation Highlights

TicketFlow focuses on the core engineering challenges of an event ticket booking system.

### Inventory Correctness

PostgreSQL is the authoritative source of truth for seat inventory.

### Concurrency

Row-level database locking prevents double booking.

### Temporary Reservations

Seat holds have configurable TTLs and automatic release.

### Waitlist Automation

Released inventory can trigger FIFO waitlist offers with a 15-minute acceptance window.

### Real-Time Experience

Seat state changes are distributed through Redis Pub/Sub and WebSockets.

### Reliable Fulfillment

QR generation and email delivery are handled through asynchronous background jobs.

### Role Isolation

Customer, organiser, and admin functionality is protected through RBAC and ownership checks.

---

# License

This project was developed as a full-stack event ticket booking system implementation project.