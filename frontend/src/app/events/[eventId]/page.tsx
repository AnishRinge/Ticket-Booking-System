"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  CalendarDays,
  Clock,
  MapPin,
  AlertCircle,
  Loader2,
  Check,
} from "lucide-react";
import api from "@/lib/api";
import type {
  ActiveHoldResponse,
  ApiResponse,
  Booking,
  BookingDetail,
  BookingList,
  EventResponse,
  SeatMapResponse,
  ShowSeat,
  HoldResponse,
} from "@/types";

interface BookingState {
  selectedSeats: Set<number>;
  holding: boolean;
  heldSeats: Set<number>;
  bookingStep: "select" | "holding" | "booking" | "success" | "error";
  error: string;
  bookingReference?: string;
  bookingId?: number;
}

export default function EventDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const eventId = parseInt(params.eventId as string);

  const [event, setEvent] = useState<EventResponse | null>(null);
  const [seatMap, setSeatMap] = useState<SeatMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [state, setState] = useState<BookingState>({
    selectedSeats: new Set(),
    holding: false,
    heldSeats: new Set(),
    bookingStep: "select",
    error: "",
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError("");

        // Fetch event details
        const eventRes = await api.get<ApiResponse<EventResponse>>(
          `/events/${eventId}`
        );
        setEvent(eventRes.data.data);

        // Fetch seat map
        const seatRes = await api.get<ApiResponse<SeatMapResponse>>(
          `/events/${eventId}/seat-map`
        );
        setSeatMap(seatRes.data.data);
      } catch (err) {
        console.error("Failed to fetch event details:", err);
        setError("Unable to load event details. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    if (eventId) {
      fetchData();
    }
  }, [eventId]);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!eventId || !token) return;

    const apiUrl = new URL(
      api.defaults.baseURL || "/api/v1",
      window.location.origin
    );
    apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
    apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, "")}/ws/events/${eventId}`;
    apiUrl.search = "";
    apiUrl.searchParams.set("token", token);

    const socket = new WebSocket(apiUrl.toString());

    socket.onmessage = (message) => {
      try {
        const update = JSON.parse(message.data) as {
          seat_id?: number;
          new_status?: string;
        };

        if (
          typeof update.seat_id !== "number" ||
          !["AVAILABLE", "HELD", "BOOKED"].includes(update.new_status || "")
        ) {
          return;
        }

        setSeatMap((current) => {
          if (!current) return current;

          return {
            ...current,
            seats: current.seats.map((seat) =>
              seat.id === update.seat_id
                ? { ...seat, status: update.new_status as ShowSeat["status"] }
                : seat
            ),
          };
        });
      } catch {
        // Ignore malformed incremental updates; REST remains authoritative.
      }
    };

    socket.onerror = () => {
      // Real-time updates are supplementary and must not block booking.
      socket.close();
    };

    return () => {
      socket.close();
    };
  }, [eventId]);

  const handleSeatClick = (seatId: number, seatStatus: string) => {
    if (seatStatus !== "AVAILABLE") return;
    if (state.bookingStep !== "select") return;

    setState((prev) => {
      const newSelected = new Set(prev.selectedSeats);
      if (newSelected.has(seatId)) {
        newSelected.delete(seatId);
      } else {
        newSelected.add(seatId);
      }
      return { ...prev, selectedSeats: newSelected };
    });
  };

  const handleHoldSeats = async () => {
    if (state.selectedSeats.size === 0) return;

    setState((prev) => ({ ...prev, holding: true, bookingStep: "holding" }));

    try {
      const heldSeatIds = new Set<number>();

      // Hold each seat individually
      for (const seatId of state.selectedSeats) {
        try {
          const response = await api.post<ApiResponse<HoldResponse>>(
            "/holds",
            { show_seat_id: seatId },
            { timeout: 5000 }
          );
          if (response.data.data.show_seat) {
            heldSeatIds.add(seatId);
          }
        } catch (err) {
          try {
            const activeHolds = await api.get<
              ApiResponse<ActiveHoldResponse>
            >("/holds");
            if (activeHolds.data.data.seats.some((seat) => seat.id === seatId)) {
              heldSeatIds.add(seatId);
              continue;
            }
          } catch (recoveryError) {
            console.error("Failed to reconcile seat hold:", recoveryError);
          }
          console.error(`Failed to hold seat ${seatId}:`, err);
        }
      }

      if (heldSeatIds.size > 0) {
        setState((prev) => ({
          ...prev,
          heldSeats: heldSeatIds,
          selectedSeats: heldSeatIds,
          holding: false,
          bookingStep: "booking",
        }));

        // Refresh seat map
        api
          .get<ApiResponse<SeatMapResponse>>(`/events/${eventId}/seat-map`)
          .then((res) => setSeatMap(res.data.data))
          .catch((err) => console.error("Failed to refresh seat map:", err));
      } else {
        setState((prev) => ({
          ...prev,
          holding: false,
          bookingStep: "error",
          error: "Failed to hold any seats. Please try again.",
        }));
      }
    } catch (err) {
      console.error("Hold error:", err);
      setState((prev) => ({
        ...prev,
        holding: false,
        bookingStep: "error",
        error: "Failed to hold seats",
      }));
    }
  };

  const handleReleaseHeldSeats = async () => {
    const heldSeatIds = Array.from(state.heldSeats);
    await Promise.allSettled(
      heldSeatIds.map((seatId) => api.delete(`/holds/${seatId}`))
    );
    setState({
      selectedSeats: new Set(),
      holding: false,
      heldSeats: new Set(),
      bookingStep: "select",
      error: "",
    });
  };

  const handleBookSeats = async () => {
    if (state.heldSeats.size === 0) return;

    setState((prev) => ({ ...prev, holding: true }));

    try {
      let booking: Booking;
      try {
        const response = await api.post<Booking>(
          "/bookings/",
          { show_seat_ids: Array.from(state.heldSeats) },
          { timeout: 5000 }
        );
        booking = response.data;
      } catch (requestError) {
        const listResponse = await api.get<BookingList>("/bookings/");
        const candidates = listResponse.data.items.filter(
          (item) => item.event_id === eventId && item.status === "CONFIRMED"
        );
        let recoveredBooking: BookingDetail | undefined;

        for (const candidate of candidates) {
          const detailResponse = await api.get<BookingDetail>(
            `/bookings/${candidate.id}`
          );
          const bookedSeatIds = detailResponse.data.booking_seats.map(
            (seat) => seat.show_seat_id
          );
          if (
            bookedSeatIds.length === state.heldSeats.size &&
            Array.from(state.heldSeats).every((seatId) =>
              bookedSeatIds.includes(seatId)
            )
          ) {
            recoveredBooking = detailResponse.data;
            break;
          }
        }

        if (!recoveredBooking) {
          throw requestError;
        }
        booking = recoveredBooking;
      }

      const bookingRef = booking.booking_reference;
      const bookingId = booking.id;
      setState((prev) => ({
        ...prev,
        holding: false,
        bookingStep: "success",
        bookingReference: bookingRef,
        bookingId: bookingId,
        selectedSeats: new Set(),
        heldSeats: new Set(),
      }));

      // Refresh seat map after booking
      try {
        const res = await api.get<ApiResponse<SeatMapResponse>>(
          `/events/${eventId}/seat-map`
        );
        setSeatMap(res.data.data);
      } catch (err) {
        console.error("Failed to refresh seat map:", err);
      }
    } catch (err: any) {
      console.error("Booking error:", err);
      setState((prev) => ({
        ...prev,
        holding: false,
        bookingStep: "error",
        error: err.response?.data?.message || "Failed to book seats",
      }));
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="flex min-h-96 items-center justify-center text-slate-400">
            <Loader2 className="animate-spin" size={32} />
          </div>
        </div>
      </main>
    );
  }

  if (error && !event) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <Link
            href="/events"
            className="mb-6 inline-flex items-center text-sm text-slate-400 transition hover:text-white"
          >
            ← Back to Events
          </Link>
          <div className="rounded-2xl border border-red-900/50 bg-red-950/30 p-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 text-red-400" />
              <div>
                <h2 className="font-semibold text-red-300">
                  Unable to load event
                </h2>
                <p className="mt-1 text-sm text-red-400">{error}</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!event || !seatMap) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <p className="text-slate-400">Event not found</p>
        </div>
      </main>
    );
  }

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString("en-IN", {
      dateStyle: "long",
      timeStyle: "short",
    });
  };

  const categoryPrices = event.category_pricings || [];
  const minPrice = categoryPrices.length
    ? Math.min(...categoryPrices.map((p) => p.price))
    : 0;

  const selectedSeatDetails = seatMap.seats.filter((s) =>
    state.selectedSeats.has(s.id)
  );
  const totalPrice = selectedSeatDetails.reduce((sum, seat) => {
    const pricing = categoryPrices.find(
      (p) => p.category_id === seat.physical_seat?.category_id
    );
    return sum + (pricing?.price || 0);
  }, 0);

  const getSeatCategory = (categoryId?: number) => {
    return event.category_pricings?.find((p) => p.category_id === categoryId)
      ?.category?.name;
  };

  const getSeatPrice = (categoryId?: number) => {
    return event.category_pricings?.find((p) => p.category_id === categoryId)
      ?.price;
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-7xl px-6 py-10">
        {/* Header */}
        <Link
          href="/events"
          className="mb-6 inline-flex items-center text-sm text-slate-400 transition hover:text-white"
        >
          <ArrowLeft size={16} className="mr-2" />
          Back to Events
        </Link>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Event Info */}
            <section>
              <h1 className="text-4xl font-bold tracking-tight">{event.title}</h1>

              {event.description && (
                <p className="mt-3 text-lg text-slate-400">{event.description}</p>
              )}

              <div className="mt-6 space-y-2 text-slate-300">
                <div className="flex items-center gap-2">
                  <CalendarDays size={18} className="text-indigo-400" />
                  <span>{formatDateTime(event.start_time)}</span>
                </div>

                {event.end_time && (
                  <div className="flex items-center gap-2">
                    <Clock size={18} className="text-indigo-400" />
                    <span>Ends {formatDateTime(event.end_time)}</span>
                  </div>
                )}

                {event.venue && (
                  <div className="flex items-center gap-2">
                    <MapPin size={18} className="text-indigo-400" />
                    <span>{event.venue.name}</span>
                  </div>
                )}
              </div>
            </section>

            {/* Seat Map */}
            {state.bookingStep !== "success" && (
              <section className="space-y-4">
                <div>
                  <h2 className="text-2xl font-bold">Select Seats</h2>
                  <p className="mt-1 text-slate-400">
                    Click on available seats to select them
                  </p>
                </div>

                {/* Seat Legend */}
                <div className="flex flex-wrap gap-4 rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 rounded border border-slate-600 bg-slate-700" />
                    <span className="text-slate-300">Available</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 rounded border border-indigo-500 bg-indigo-600" />
                    <span className="text-slate-300">Selected</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 rounded border border-slate-600 bg-red-600/40" />
                    <span className="text-slate-300">Held/Booked</span>
                  </div>
                </div>

                {/* Seat Grid */}
                <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/50 p-8">
                  <div className="inline-block space-y-3 min-w-max">
                    {/* Group seats by row */}
                    {Array.from(
                      new Set(
                        seatMap.seats
                          .filter((s) => s.physical_seat)
                          .map((s) => s.physical_seat!.row_identifier)
                      )
                    )
                      .sort()
                      .map((row) => (
                        <div key={row} className="flex items-center gap-2">
                          <div className="w-8 text-center text-sm font-semibold text-slate-400">
                            {row}
                          </div>

                          <div className="flex gap-2">
                            {seatMap.seats
                              .filter(
                                (s) => s.physical_seat?.row_identifier === row
                              )
                              .sort(
                                (a, b) =>
                                  (a.physical_seat?.seat_number || 0) -
                                  (b.physical_seat?.seat_number || 0)
                              )
                              .map((seat) => (
                                <button
                                  key={seat.id}
                                  onClick={() =>
                                    handleSeatClick(seat.id, seat.status)
                                  }
                                  disabled={
                                    seat.status !== "AVAILABLE" ||
                                    state.bookingStep !== "select"
                                  }
                                  title={`${seat.physical_seat?.row_identifier}${seat.physical_seat?.seat_number} - ${getSeatCategory(seat.physical_seat?.category_id)} (₹${getSeatPrice(seat.physical_seat?.category_id)})`}
                                  className={`h-8 w-8 rounded border text-xs font-medium transition ${
                                    state.selectedSeats.has(seat.id)
                                      ? "border-indigo-500 bg-indigo-600 text-white"
                                      : seat.status === "AVAILABLE"
                                        ? "border-slate-600 bg-slate-700 text-slate-300 hover:border-indigo-400 hover:bg-indigo-600/30 cursor-pointer"
                                        : "border-slate-600 bg-red-600/40 text-slate-400 cursor-not-allowed"
                                  }`}
                                >
                                  {seat.physical_seat?.seat_number}
                                </button>
                              ))}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </section>
            )}

            {/* Success Message */}
            {state.bookingStep === "success" && state.bookingReference && (
              <section className="rounded-lg border border-emerald-500/50 bg-emerald-950/30 p-8 text-center">
                <div className="flex justify-center mb-4">
                  <Check className="h-12 w-12 text-emerald-400" />
                </div>
                <h2 className="text-2xl font-bold text-emerald-300">
                  Booking Confirmed!
                </h2>
                <p className="mt-3 text-lg text-emerald-200">
                  Booking Reference: <span className="font-mono font-bold">{state.bookingReference}</span>
                </p>
                <p className="mt-2 text-sm text-emerald-300/70">
                  Your booking has been successfully created. You can view your ticket in your booking details.
                </p>
                <div className="mt-6 flex gap-4 justify-center">
                  <button
                    onClick={() => router.push(`/bookings/${state.bookingId}`)}
                    className="rounded-lg bg-emerald-600 px-6 py-2 font-medium text-white transition hover:bg-emerald-500"
                  >
                    View Booking
                  </button>
                  <button
                    onClick={() => {
                      setState({
                        selectedSeats: new Set(),
                        holding: false,
                        heldSeats: new Set(),
                        bookingStep: "select",
                        error: "",
                      });
                    }}
                    className="rounded-lg border border-emerald-500 px-6 py-2 font-medium text-emerald-300 transition hover:bg-emerald-500/10"
                  >
                    Book More Seats
                  </button>
                </div>
              </section>
            )}

            {/* Error Message */}
            {state.bookingStep === "error" && state.error && (
              <section className="rounded-lg border border-red-900/50 bg-red-950/30 p-6">
                <div className="flex items-start gap-3">
                  <AlertCircle className="mt-0.5 h-5 w-5 text-red-400" />
                  <div>
                    <h3 className="font-semibold text-red-300">Booking Error</h3>
                    <p className="mt-1 text-sm text-red-400">{state.error}</p>
                    <button
                      onClick={() =>
                        setState((prev) => ({
                          ...prev,
                          bookingStep: "select",
                          error: "",
                        }))
                      }
                      className="mt-3 rounded bg-red-500/10 px-3 py-1 text-sm font-medium text-red-300 transition hover:bg-red-500/20"
                    >
                      Try Again
                    </button>
                  </div>
                </div>
              </section>
            )}
          </div>

          {/* Sidebar - Summary */}
          <div className="lg:col-span-1">
            <div className="sticky top-6 space-y-6">
              {/* Summary Card */}
              <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
                <h3 className="font-semibold text-lg text-white">
                  Order Summary
                </h3>

                {state.selectedSeats.size > 0 ? (
                  <div className="mt-4 space-y-3">
                    <div className="space-y-2 rounded bg-slate-800/50 p-3 text-sm">
                      <p className="text-slate-300">
                        Selected Seats ({state.selectedSeats.size}):
                      </p>
                      <div className="space-y-1">
                        {selectedSeatDetails
                          .sort(
                            (a, b) =>
                              (a.physical_seat?.seat_number || 0) -
                              (b.physical_seat?.seat_number || 0)
                          )
                          .map((seat) => (
                            <div
                              key={seat.id}
                              className="flex items-center justify-between text-xs text-slate-300"
                            >
                              <span>
                                {seat.physical_seat?.row_identifier}
                                {seat.physical_seat?.seat_number} -{" "}
                                {getSeatCategory(seat.physical_seat?.category_id)}
                              </span>
                              <span className="font-medium">
                                ₹
                                {getSeatPrice(
                                  seat.physical_seat?.category_id
                                )?.toLocaleString("en-IN")}
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>

                    <div className="border-t border-slate-700 pt-3">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-300">Total:</span>
                        <span className="text-xl font-bold text-white">
                          ₹{totalPrice.toLocaleString("en-IN")}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-slate-400">
                    Select seats to see summary
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              {state.bookingStep !== "success" && (
                <div className="space-y-3">
                  {state.bookingStep === "select" && (
                    <button
                      onClick={handleHoldSeats}
                      disabled={
                        state.selectedSeats.size === 0 || state.holding
                      }
                      className={`w-full rounded-lg px-4 py-3 font-semibold transition ${
                        state.selectedSeats.size === 0
                          ? "cursor-not-allowed bg-slate-700 text-slate-400"
                          : "bg-indigo-600 text-white hover:bg-indigo-500"
                      }`}
                    >
                      {state.holding ? (
                        <span className="flex items-center justify-center gap-2">
                          <Loader2 size={18} className="animate-spin" />
                          Holding Seats...
                        </span>
                      ) : (
                        "Hold Seats"
                      )}
                    </button>
                  )}

                  {state.bookingStep === "booking" && (
                    <>
                      <button
                        onClick={handleBookSeats}
                        disabled={state.holding}
                        className="w-full rounded-lg bg-emerald-600 px-4 py-3 font-semibold text-white transition hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-400"
                      >
                        {state.holding ? (
                          <span className="flex items-center justify-center gap-2">
                            <Loader2 size={18} className="animate-spin" />
                            Confirming...
                          </span>
                        ) : (
                          `Confirm Booking - ₹${totalPrice.toLocaleString("en-IN")}`
                        )}
                      </button>
                      <button
                        onClick={handleReleaseHeldSeats}
                        disabled={state.holding}
                        className="w-full rounded-lg border border-slate-600 px-4 py-3 font-semibold text-slate-300 transition hover:bg-slate-800"
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </div>
              )}

              {state.bookingStep === "success" && (
                <button
                  onClick={() => router.push("/dashboard/customer")}
                  className="w-full rounded-lg border border-slate-600 px-4 py-3 font-semibold text-slate-300 transition hover:bg-slate-800"
                >
                  Back to Dashboard
                </button>
              )}

              {/* Category Info */}
              <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
                <h4 className="text-sm font-semibold text-slate-300">
                  Seat Categories
                </h4>
                <div className="mt-3 space-y-2 text-sm">
                  {event.category_pricings?.map((pricing) => (
                    <div
                      key={pricing.id}
                      className="flex items-center justify-between text-slate-400"
                    >
                      <span>{pricing.category?.name}</span>
                      <span className="font-medium">
                        ₹{pricing.price.toLocaleString("en-IN")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
