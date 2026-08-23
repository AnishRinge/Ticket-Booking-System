from datetime import datetime
from typing import List

def get_booking_confirmation_body(
    event_title: str,
    event_date: datetime,
    venue_name: str,
    booking_reference: str,
    seats: List[str],
    total_price: float,
) -> str:
    """
    Returns the plain text body for booking confirmation email.
    """
    seat_str = ", ".join(seats)
    return f"""
Hi there!

Your booking for {event_title} is confirmed.

Booking Details:
----------------
Event: {event_title}
Date/Time: {event_date.strftime('%Y-%m-%d %H:%M')}
Venue: {venue_name}
Booking Reference: {booking_reference}
Seats: {seat_str}
Total Price: {total_price}

Your QR ticket is attached to this email. Please present it at the venue.

Thank you for booking with us!
"""

def get_waitlist_offer_body(
    event_title: str,
    venue_name: str,
    category_name: str,
    expiry_time: datetime,
) -> str:
    """
    Returns the plain text body for waitlist offer email.
    """
    return f"""
Hi!

Good news! A seat has become available for {event_title}.

As you were on the waitlist, we are offering you the chance to book this seat.

Offer Details:
--------------
Event: {event_title}
Venue: {venue_name}
Category: {category_name}
Expires at: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}

To accept this offer, please log in to your account and complete the booking before the expiry time.

Best regards,
Ticket Booking Team
"""
