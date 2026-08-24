# TicketFlow — System Design

## 1. Seat Hold and TTL Mechanism

TicketFlow separates physical seats from event-specific inventory using the `ShowSeat` entity. Each `ShowSeat` has a state:

```text
AVAILABLE → HELD → BOOKED
             │
             └── TTL expiry → AVAILABLE
```

When a customer selects a seat, the backend changes the corresponding `ShowSeat` from `AVAILABLE` to `HELD`. The hold stores both the customer identity (`held_by_id`) and an expiration timestamp (`hold_expires_at`).

The hold duration is configurable through `SEAT_HOLD_TTL_SECONDS`.

Before a booking can be confirmed, the backend verifies that the seat is still held, that the current customer owns the hold, and that the expiration timestamp has not been reached.

Once the booking transaction succeeds, the seat changes from `HELD` to `BOOKED`.

Expired holds are processed by the background scheduler and returned to `AVAILABLE`, making the inventory available again.

The frontend countdown is only a presentation mechanism. The backend and database determine whether a hold is valid.

---

## 2. Concurrency Prevention

Seat inventory is protected using PostgreSQL transactions and row-level locking.

For hold and booking operations, the backend locks the requested `ShowSeat` rows using:

```sql
SELECT ... FOR UPDATE
```

For multi-seat operations, seat IDs are sorted before acquiring locks. This provides a deterministic locking order and reduces the possibility of transaction deadlocks.

During booking, the locked seats are validated for:

1. Existence
2. Current `HELD` status
3. Hold ownership
4. Hold expiration
5. Event consistency
6. Category pricing

Only after all validations succeed does the transaction create the `Booking` and `BookingSeat` records and change the seats to `BOOKED`.

Because competing transactions cannot simultaneously modify the same locked inventory rows, two customers cannot successfully book the same seat.

PostgreSQL therefore acts as the authoritative source of truth for inventory state.

---

## 3. Waitlist Auto-Assignment Flow

Waitlists are maintained for a specific event and seat category.

Customers are inserted into the waitlist in FIFO order. Each entry records the customer, event, category, and queue position through its creation order.

When inventory becomes available, either because a booking is cancelled or a seat hold expires, the waitlist service checks for eligible customers.

The flow is:

```text
Seat Released
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

This allows released inventory to be automatically offered to the next eligible customer instead of requiring manual intervention.

Waitlist processing is integrated with seat-release operations so newly available inventory can immediately enter the waitlist allocation flow.

---

## 4. Time-Limited Waitlist Offers

A waitlist offer is temporary and contains an explicit expiration timestamp.

The configured offer duration is controlled through:

```text
WAITLIST_OFFER_TTL_SECONDS
```

The project uses:

```text
900 seconds = 15 minutes
```

When an offer is created, its expiration time is stored by the backend.

The customer must accept the offer within this period. The frontend may display a countdown, but the backend remains authoritative when determining whether the offer is still valid.

A background scheduler periodically identifies expired waitlist offers and cleans them up. Once an offer expires, the inventory can continue through the waitlist process and be offered to the next eligible customer.

This design prevents inventory from remaining indefinitely reserved for one waitlisted customer while maintaining a fair FIFO allocation process.

---

## Summary

TicketFlow combines temporary inventory reservation, transactional database locking, automated waitlist allocation, and time-limited offers to maintain reliable ticket inventory under concurrent booking requests.

The core design principles are:

```text
PostgreSQL → authoritative inventory state
Row Locks  → concurrency protection
TTL        → temporary seat reservation
FIFO       → fair waitlist ordering
Offers     → time-limited waitlist allocation
Scheduler  → automatic expiration handling
```