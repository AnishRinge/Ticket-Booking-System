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
  Trash2,
} from "lucide-react";
import api from "@/lib/api";
import type { BookingDetail } from "@/types";

export default function BookingDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = parseInt(params.bookingId as string);

  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState("");
  const [cancelled, setCancelled] = useState(false);

  useEffect(() => {
    const fetchBooking = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await api.get<BookingDetail>(
          `/bookings/${bookingId}`
        );
        setBooking(response.data);
      } catch (err: any) {
        console.error("Failed to fetch booking:", err);
        setError(
          err.response?.data?.message || "Unable to load booking details"
        );
      } finally {
        setLoading(false);
      }
    };

    if (bookingId) {
      fetchBooking();
    }
  }, [bookingId]);

  const handleCancelBooking = async () => {
    if (!booking) return;

    setCancelling(true);
    setCancelError("");

    try {
      try {
        await api.post(`/bookings/${bookingId}/cancel`, undefined, {
          timeout: 5000,
        });
      } catch (requestError) {
        const detailResponse = await api.get<BookingDetail>(
          `/bookings/${bookingId}`
        );
        if (detailResponse.data.status !== "CANCELLED") {
          throw requestError;
        }
        setBooking(detailResponse.data);
        setCancelled(true);
        return;
      }

      const response = await api.get<BookingDetail>(`/bookings/${bookingId}`);
      setBooking(response.data);
      setCancelled(response.data.status === "CANCELLED");
    } catch (err: any) {
      console.error("Failed to cancel booking:", err);
      setCancelError(
        err.response?.data?.message || "Failed to cancel booking"
      );
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto max-w-4xl px-6 py-10">
          <div className="flex min-h-96 items-center justify-center text-slate-400">
            <Loader2 className="animate-spin" size={32} />
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto max-w-4xl px-6 py-10">
          <Link
            href="/dashboard/customer/bookings"
            className="mb-6 inline-flex items-center text-sm text-slate-400 transition hover:text-white"
          >
            <ArrowLeft size={16} className="mr-2" />
            Back to Bookings
          </Link>
          <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 text-red-400" />
              <div>
                <h2 className="font-semibold text-red-300">
                  Unable to load booking
                </h2>
                <p className="mt-1 text-sm text-red-400">{error}</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!booking) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto max-w-4xl px-6 py-10">
          <p className="text-slate-400">Booking not found</p>
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("en-IN", {
      dateStyle: "long",
    });
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-4xl px-6 py-10">
        {/* Header */}
        <Link
          href="/dashboard/customer/bookings"
          className="mb-6 inline-flex items-center text-sm text-slate-400 transition hover:text-white"
        >
          <ArrowLeft size={16} className="mr-2" />
          Back to Bookings
        </Link>

        {/* Cancellation Success */}
        {cancelled && (
          <div className="mb-6 rounded-lg border border-emerald-500/50 bg-emerald-950/30 p-4">
            <p className="text-sm text-emerald-300">
              Booking has been cancelled successfully.
            </p>
          </div>
        )}

        {/* Cancellation Error */}
        {cancelError && (
          <div className="mb-6 rounded-lg border border-red-900/50 bg-red-950/30 p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 text-red-400" />
              <p className="text-sm text-red-300">{cancelError}</p>
            </div>
          </div>
        )}

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Main Ticket */}
          <div className="lg:col-span-2">
            <div className="rounded-lg border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 overflow-hidden">
              {/* Ticket Header */}
              <div className="border-b border-slate-800 bg-gradient-to-r from-indigo-600 to-indigo-700 p-6 text-white">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-indigo-100 uppercase tracking-wider">
                      Booking Confirmation
                    </p>
                    <h1 className="mt-2 text-3xl font-bold">
                      {booking.event.title}
                    </h1>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-indigo-100">Reference</p>
                    <p className="mt-1 font-mono text-xl font-bold">
                      {booking.booking_reference}
                    </p>
                  </div>
                </div>
              </div>

              {/* Event Details */}
              <div className="border-b border-slate-800 p-6 space-y-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Event
                  </p>
                  <p className="mt-2 text-lg font-medium text-white">
                    {booking.event.title}
                  </p>
                  {booking.event.description && (
                    <p className="mt-2 text-sm text-slate-400">
                      {booking.event.description}
                    </p>
                  )}
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Date & Time
                    </p>
                    <div className="mt-2 flex items-center gap-2 text-white">
                      <CalendarDays size={16} className="text-indigo-400" />
                      <span>{formatDateTime(booking.event.start_time)}</span>
                    </div>
                  </div>

                  {booking.event.venue && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Venue
                      </p>
                      <div className="mt-2 flex items-center gap-2 text-white">
                        <MapPin size={16} className="text-indigo-400" />
                        <span>{booking.event.venue.name}</span>
                      </div>
                    </div>
                  )}

                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Booking Date
                    </p>
                    <p className="mt-2 text-white">{formatDate(booking.created_at)}</p>
                  </div>
                </div>
              </div>

              {/* Seats */}
              <div className="border-b border-slate-800 p-6">
                <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Reserved Seats ({booking.booking_seats.length})
                </p>

                <div className="space-y-2">
                  {booking.booking_seats.map((seat) => (
                    <div
                      key={seat.id}
                      className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-3"
                    >
                      <div>
                        <p className="font-medium text-white">
                          Seat {seat.show_seat_id}
                        </p>
                        <p className="text-xs text-slate-400">
                          {/* Physical seat details would go here if available */}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-white">
                          ₹{seat.price_at_booking.toLocaleString("en-IN")}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Total */}
              <div className="bg-slate-800/50 p-6">
                <div className="flex items-center justify-between">
                  <span className="text-lg font-semibold text-white">
                    Total
                  </span>
                  <span className="text-3xl font-bold text-indigo-400">
                    ₹{booking.total_price.toLocaleString("en-IN")}
                  </span>
                </div>
              </div>

              {/* Status */}
              <div className="border-t border-slate-800 p-6">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-400">
                    Status
                  </span>
                  <span
                    className={`rounded-full px-4 py-1 text-sm font-semibold ${
                      booking.status === "CONFIRMED"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {booking.status}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="sticky top-6 space-y-4">
              {/* Summary */}
              <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
                <h3 className="font-semibold text-white">Summary</h3>

                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex items-center justify-between text-slate-300">
                    <span>Seats</span>
                    <span className="font-medium">
                      {booking.booking_seats.length}
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-t border-slate-700 pt-3 text-white">
                    <span className="font-semibold">Total</span>
                    <span className="font-bold">
                      ₹{booking.total_price.toLocaleString("en-IN")}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="space-y-2">
                {booking.status === "CONFIRMED" && (
                  <button
                    onClick={handleCancelBooking}
                    disabled={cancelling}
                    className="w-full rounded-lg border border-red-600 px-4 py-3 font-semibold text-red-300 transition hover:bg-red-500/10 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {cancelling ? (
                      <>
                        <Loader2 size={18} className="animate-spin" />
                        Cancelling...
                      </>
                    ) : (
                      <>
                        <Trash2 size={18} />
                        Cancel Booking
                      </>
                    )}
                  </button>
                )}

                <button
                  onClick={() => router.push("/dashboard/customer")}
                  className="w-full rounded-lg bg-slate-800 px-4 py-3 font-semibold text-slate-300 transition hover:bg-slate-700"
                >
                  Back to Dashboard
                </button>
              </div>

              {/* Info */}
              <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-xs text-slate-400">
                <p className="leading-relaxed">
                  Your booking reference is <strong className="text-white">{booking.booking_reference}</strong>. Keep this for your records.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
