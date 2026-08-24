"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CalendarDays, Clock, MapPin, Ticket, AlertCircle } from "lucide-react";
import api from "@/lib/api";
import type { ApiResponse } from "@/types";

interface EventResponse {
  id: number;
  title: string;
  description: string | null;
  venue_id: number;
  start_time: string;
  end_time: string | null;
  organiser_id: number;
  organiser: {
    id: number;
    name?: string;
    email?: string;
  } | null;
  category_pricings: Array<{
    id: number;
    category_id: number;
    price: number;
    category?: {
      id?: number;
      name?: string;
    } | null;
  }>;
  venue: {
    id?: number;
    name?: string;
    address?: string;
    city?: string;
  } | null;
}

export default function EventsPage() {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await api.get<ApiResponse<EventResponse[]>>("/events");
        setEvents(response.data.data);
      } catch (err) {
        console.error("Failed to fetch events:", err);
        setError("Unable to load events. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, []);

  const formatDateTime = (value: string) => {
    return new Date(value).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };

  const getStartingPrice = (event: EventResponse) => {
    if (!event.category_pricings.length) {
      return null;
    }

    return Math.min(
      ...event.category_pricings.map((pricing) => pricing.price)
    );
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-7xl px-6 py-10">
        {/* Header */}
        <div className="mb-10">
          <Link
            href="/dashboard"
            className="mb-6 inline-flex items-center text-sm text-slate-400 transition hover:text-white"
          >
            ← Back to Dashboard
          </Link>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-3 flex items-center gap-2 text-indigo-400">
                <Ticket className="h-5 w-5" />
                <span className="text-sm font-semibold uppercase tracking-wider">
                  TicketFlow
                </span>
              </div>

              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Discover Events
              </h1>

              <p className="mt-2 max-w-2xl text-slate-400">
                Browse upcoming events and choose your seats.
              </p>
            </div>

            {!loading && !error && (
              <div className="text-sm text-slate-400">
                {events.length} {events.length === 1 ? "event" : "events"} available
              </div>
            )}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((item) => (
              <div
                key={item}
                className="h-72 animate-pulse rounded-2xl border border-slate-800 bg-slate-900"
              />
            ))}
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="rounded-2xl border border-red-900/50 bg-red-950/30 p-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 text-red-400" />

              <div>
                <h2 className="font-semibold text-red-300">
                  Unable to load events
                </h2>
                <p className="mt-1 text-sm text-red-400">{error}</p>

                <button
                  onClick={() => window.location.reload()}
                  className="mt-4 rounded-lg bg-red-500/10 px-4 py-2 text-sm font-medium text-red-300 transition hover:bg-red-500/20"
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && events.length === 0 && (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 px-6 py-16 text-center">
            <Ticket className="mx-auto h-10 w-10 text-slate-600" />

            <h2 className="mt-4 text-xl font-semibold">
              No events available
            </h2>

            <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
              There are currently no events available for booking.
            </p>
          </div>
        )}

        {/* Events */}
        {!loading && !error && events.length > 0 && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {events.map((event) => {
              const startingPrice = getStartingPrice(event);

              return (
                <Link
                  key={event.id}
                  href={`/events/${event.id}`}
                  className="group overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 transition hover:-translate-y-1 hover:border-indigo-500/50 hover:bg-slate-900/90"
                >
                  {/* Card top */}
                  <div className="flex h-32 items-center justify-center bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-950">
                    <Ticket className="h-12 w-12 text-indigo-400 transition group-hover:scale-110" />
                  </div>

                  <div className="p-6">
                    <h2 className="line-clamp-2 text-xl font-semibold transition group-hover:text-indigo-400">
                      {event.title}
                    </h2>

                    {event.description && (
                      <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-400">
                        {event.description}
                      </p>
                    )}

                    <div className="mt-5 space-y-3 text-sm text-slate-300">
                      <div className="flex items-start gap-3">
                        <CalendarDays className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                        <span>{formatDateTime(event.start_time)}</span>
                      </div>

                      {event.end_time && (
                        <div className="flex items-start gap-3">
                          <Clock className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                          <span>
                            Ends {formatDateTime(event.end_time)}
                          </span>
                        </div>
                      )}

                      {event.venue && (
                        <div className="flex items-start gap-3">
                          <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                          <span>
                            {event.venue.name ||
                              event.venue.city ||
                              `Venue #${event.venue_id}`}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="mt-6 flex items-center justify-between border-t border-slate-800 pt-5">
                      <div>
                        <p className="text-xs text-slate-500">
                          Starting from
                        </p>

                        <p className="mt-1 text-lg font-bold text-white">
                          {startingPrice !== null
                            ? `₹${startingPrice.toLocaleString("en-IN")}`
                            : "Price unavailable"}
                        </p>
                      </div>

                      <span className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition group-hover:bg-indigo-400">
                        View Event
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}