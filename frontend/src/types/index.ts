// User & Auth
export type UserRole = "CUSTOMER" | "ORGANISER" | "ADMIN";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface UserShortResponse {
  id: number;
  email?: string;
  full_name?: string;
}

export interface ApiResponse<T> {
  message: string;
  data: T;
  status_code: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  role?: UserRole;
}

// Venues & Seats
export type SeatStatus = "AVAILABLE" | "HELD" | "BOOKED";

export interface SeatCategory {
  id: number;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Seat {
  id: number;
  venue_id: number;
  category_id: number;
  row_identifier: string;
  seat_number: number;
  x_pos?: number;
  y_pos?: number;
  category?: SeatCategory;
  created_at?: string;
  updated_at?: string;
}

export interface SeatWithCategory extends Seat {
  category: SeatCategory;
}

export interface Venue {
  id: number;
  name: string;
  address: string;
  created_at?: string;
  updated_at?: string;
}

// Inventory
export interface ShowSeat {
  id: number;
  event_id: number;
  physical_seat_id: number;
  status: SeatStatus;
  held_by_id?: number | null;
  hold_expires_at?: string | null;
  physical_seat?: SeatWithCategory;
  created_at?: string;
  updated_at?: string;
}

export interface SeatMapResponse {
  event_id: number;
  seats: ShowSeat[];
}

// Events
export interface EventCategoryPricing {
  id: number;
  category_id: number;
  price: number;
  category?: SeatCategory;
  created_at?: string;
  updated_at?: string;
}

export interface Event {
  id: number;
  title: string;
  description?: string;
  venue_id: number;
  organiser_id: number;
  start_time: string;
  end_time?: string;
  category_pricings?: EventCategoryPricing[];
  organiser?: UserShortResponse;
  venue?: Venue;
  created_at?: string;
  updated_at?: string;
}

export interface EventResponse extends Event {
  category_pricings: EventCategoryPricing[];
}

// Holds
export interface HoldCreate {
  show_seat_id: number;
}

export interface HoldResponse {
  show_seat: ShowSeat;
  message: string;
}

export interface ActiveHoldResponse {
  seats: ShowSeat[];
}

// Bookings
export interface BookingSeat {
  id: number;
  booking_id: number;
  show_seat_id: number;
  price_at_booking: number;
  created_at?: string;
  updated_at?: string;
}

export interface Booking {
  id: number;
  booking_reference: string;
  user_id: number;
  event_id: number;
  status: "CONFIRMED" | "CANCELLED";
  total_price: number;
  created_at: string;
  updated_at: string;
}

export interface BookingCreate {
  show_seat_ids: number[];
}

export interface BookingDetail extends Booking {
  event: EventResponse;
  booking_seats: BookingSeat[];
}

export interface BookingList {
  total: number;
  items: Booking[];
}

// Dashboards
export interface EventSummary {
  id: number;
  title: string;
  bookings_count: number;
  revenue: number;
  start_time: string;
  status: string;
}

export interface OrganiserDashboard {
  total_events: number;
  total_bookings: number;
  total_revenue: number;
  recent_events: EventSummary[];
}

export interface RecentBooking {
  id: number;
  reference: string;
  user_email: string;
  event_title: string;
  status: string;
  total_price: number;
  created_at: string;
}

export interface AdminDashboard {
  total_venues: number;
  total_events: number;
  total_revenue: number;
  total_users: number;
  recent_bookings: RecentBooking[];
}
