"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  CalendarDays,
  Check,
  Clock,
  Loader2,
  MapPin,
  Plus,
  Ticket,
} from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import api from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import type {
  ApiResponse,
  EventCreate,
  EventResponse,
  SeatCategory,
  Venue,
} from "@/types";

function formatDate(value: string) {
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function OrganiserEventsPage() {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [categories, setCategories] = useState<SeatCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Create Event Form State
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [venueId, setVenueId] = useState<number | "">("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");

  // Pricing per category map
  const [categoryPrices, setCategoryPrices] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState(false);

  async function loadData() {
    try {
      setLoading(true);
      const [user, eventsRes, venuesRes, categoriesRes] = await Promise.all([
        getCurrentUser(),
        api.get<ApiResponse<EventResponse[]>>("/events"),
        api.get<ApiResponse<Venue[]>>("/venues"),
        api.get<ApiResponse<SeatCategory[]>>("/venues/categories"),
      ]);

      const userEvents = eventsRes.data.data.filter(
        (event) => event.organiser_id === user.id
      );
      setEvents(userEvents);

      const fetchedVenues = venuesRes.data.data;
      setVenues(fetchedVenues);
      if (fetchedVenues.length > 0 && venueId === "") {
        setVenueId(fetchedVenues[0].id);
      }

      const fetchedCategories = categoriesRes.data.data;
      setCategories(fetchedCategories);

      const initialPrices: Record<number, string> = {};
      fetchedCategories.forEach((cat) => {
        initialPrices[cat.id] = "500";
      });
      setCategoryPrices(initialPrices);

      setError("");
    } catch {
      setError("Unable to load your events and system configuration.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function handlePriceChange(catId: number, val: string) {
    setCategoryPrices((prev) => ({ ...prev, [catId]: val }));
  }

  async function handleCreateEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!title.trim() || !venueId || !startTime) {
      setError("Please fill in all required fields (title, venue, start time).");
      return;
    }

    const start = new Date(startTime);
    if (start <= new Date()) {
      setError("Event start time must be in the future.");
      return;
    }

    if (endTime) {
      const end = new Date(endTime);
      if (end <= start) {
        setError("Event end time must be after the start time.");
        return;
      }
    }

    const pricings = categories
      .map((cat) => {
        const rawPrice = categoryPrices[cat.id];
        if (rawPrice !== undefined && rawPrice !== "" && !isNaN(Number(rawPrice))) {
          return {
            category_id: cat.id,
            price: Number(rawPrice),
          };
        }
        return null;
      })
      .filter(Boolean) as { category_id: number; price: number }[];

    if (pricings.length === 0) {
      setError("Please specify pricing for at least one seat category.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const payload: EventCreate = {
        title: title.trim(),
        description: description.trim() || undefined,
        venue_id: Number(venueId),
        start_time: new Date(startTime).toISOString(),
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
        category_pricings: pricings,
      };

      const res = await api.post<ApiResponse<EventResponse>>("/events", payload);
      const newEvent = res.data.data;

      setEvents((prev) => [newEvent, ...prev]);
      setSuccess(`Event "${newEvent.title}" created successfully.`);

      setTitle("");
      setDescription("");
      setStartTime("");
      setEndTime("");
      setShowCreateForm(false);
    } catch (err: any) {
      setError(
        err.response?.data?.message || "Failed to create event. Please check inputs."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardShell role="ORGANISER" title="Events">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <section>
            <h2 className="text-2xl font-semibold text-white">Your events</h2>
            <p className="mt-1 text-sm text-slate-500">
              Manage and review events owned by your account.
            </p>
          </section>

          <button
            onClick={() => {
              setShowCreateForm((prev) => !prev);
              setError("");
              setSuccess("");
            }}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500"
          >
            <Plus size={16} /> {showCreateForm ? "Close Form" : "Create Event"}
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-900 bg-red-950/30 p-4 text-red-300 text-sm">
            <AlertCircle className="mt-0.5 shrink-0" size={18} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-900 bg-emerald-950/30 p-4 text-emerald-300 text-sm">
            <Check size={18} />
            <span>{success}</span>
          </div>
        )}

        {showCreateForm && (
          <form
            onSubmit={handleCreateEvent}
            className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-4"
          >
            <h3 className="text-lg font-semibold text-white">Create New Event</h3>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-slate-400">
                  Event Title <span className="text-red-400">*</span>
                </label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Summer Music Festival 2026"
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400">
                  Venue <span className="text-red-400">*</span>
                </label>
                <select
                  value={venueId}
                  onChange={(e) => setVenueId(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  required
                >
                  <option value="" disabled>Select a venue</option>
                  {venues.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} ({v.address})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400">
                Description (Optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Event summary and details..."
                rows={3}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-slate-400">
                  Start Time <span className="text-red-400">*</span>
                </label>
                <input
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400">
                  End Time (Optional)
                </label>
                <input
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-3">
              <h4 className="text-sm font-semibold text-white">Seat Category Pricing</h4>
              <p className="text-xs text-slate-500">
                Specify ticket pricing (in ₹) for seat categories available at the venue.
              </p>

              {categories.length === 0 ? (
                <p className="text-xs text-slate-500">
                  No seat categories found. Admin must configure seat categories first.
                </p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                  {categories.map((cat) => (
                    <div key={cat.id} className="space-y-1">
                      <label className="block text-xs font-medium text-slate-300">
                        {cat.name} (ID: {cat.id})
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-2.5 text-xs text-slate-500">₹</span>
                        <input
                          type="number"
                          min={0}
                          step={10}
                          value={categoryPrices[cat.id] ?? ""}
                          onChange={(e) => handlePriceChange(cat.id, e.target.value)}
                          placeholder="Price"
                          className="w-full rounded-lg border border-slate-700 bg-slate-900 pl-7 pr-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                          required
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Save Event
              </button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="flex min-h-64 items-center justify-center text-slate-400">Loading events...</div>
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
