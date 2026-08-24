"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, CalendarDays, Clock, MapPin, Ticket } from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import api from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import type { ApiResponse, EventResponse, User } from "@/types";

function formatDate(value: string) {
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function OrganiserEventsPage() {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadEvents() {
      try {
        const [user, response] = await Promise.all([
          getCurrentUser(),
          api.get<ApiResponse<EventResponse[]>>("/events"),
        ]);
        setEvents(response.data.data.filter((event) => event.organiser_id === user.id));
      } catch {
        setError("Unable to load your events.");
      } finally {
        setLoading(false);
      }
    }

    loadEvents();
  }, []);

  return (
    <DashboardShell role="ORGANISER" title="Events">
      <div className="space-y-6">
        <section>
          <h2 className="text-2xl font-semibold text-white">Your events</h2>
          <p className="mt-1 text-sm text-slate-500">Manage and review events owned by your account.</p>
        </section>

        {loading ? (
          <div className="flex min-h-64 items-center justify-center text-slate-400">Loading events...</div>
        ) : error ? (
          <div className="flex items-start gap-3 rounded-xl border border-red-900 bg-red-950/30 p-6 text-red-300">
            <AlertCircle className="mt-0.5" size={20} />
            <span>{error}</span>
          </div>
        ) : events.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900 px-6 py-16 text-center">
            <Ticket className="mx-auto text-slate-600" size={36} />
            <h3 className="mt-4 font-medium text-white">No events found</h3>
            <p className="mt-1 text-sm text-slate-500">Events owned by your account will appear here.</p>
          </div>
        ) : (
          <section className="grid gap-4 md:grid-cols-2">
            {events.map((event) => {
              const status = new Date(event.start_time) > new Date() ? "Upcoming" : "Completed";
              return (
                <article key={event.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h3 className="truncate text-lg font-semibold text-white">{event.title}</h3>
                      <p className="mt-1 text-xs text-slate-500">Event ID: {event.id}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${status === "Upcoming" ? "bg-blue-500/10 text-blue-400" : "bg-slate-700 text-slate-300"}`}>
                      {status}
                    </span>
                  </div>

                  <div className="mt-5 space-y-3 text-sm text-slate-300">
                    <div className="flex items-center gap-3"><CalendarDays size={16} className="text-blue-400" />{formatDate(event.start_time)}</div>
                    {event.end_time && <div className="flex items-center gap-3"><Clock size={16} className="text-blue-400" />Ends {formatDate(event.end_time)}</div>}
                    <div className="flex items-center gap-3"><MapPin size={16} className="text-blue-400" />{event.venue?.name ?? `Venue #${event.venue_id}`}</div>
                  </div>

                  <Link href={`/events/${event.id}`} className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-blue-400 hover:text-blue-300">
                    <Ticket size={16} /> View event details
                  </Link>
                </article>
              );
            })}
          </section>
        )}
      </div>
    </DashboardShell>
  );
}
