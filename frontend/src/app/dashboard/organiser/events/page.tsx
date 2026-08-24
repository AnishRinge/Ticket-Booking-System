"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  CalendarDays,
  Check,
  CheckCircle2,
  Clock,
  Layers,
  Loader2,
  MapPin,
  Plus,
  Ticket,
  Trash2,
} from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import api from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import type {
  ApiResponse,
  EventCreate,
  EventResponse,
  SeatCategory,
  SeatMapResponse,
  ShowSeat,
  Venue,
} from "@/types";

function formatDate(value: string) {
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

interface InventoryStatus {
  initialized: boolean;
  count: number;
}

export default function OrganiserEventsPage() {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [categories, setCategories] = useState<SeatCategory[]>([]);
  const [inventoryMap, setInventoryMap] = useState<Record<number, InventoryStatus>>({});
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
  const [initializingEventId, setInitializingEventId] = useState<number | null>(null);
  const [deletingEventId, setDeletingEventId] = useState<number | null>(null);

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

      // Check seat map / inventory status for each organiser event
      const invStatusMap: Record<number, InventoryStatus> = {};
      await Promise.all(
        userEvents.map(async (event) => {
          try {
            const seatMapRes = await api.get<ApiResponse<SeatMapResponse>>(
              `/events/${event.id}/seat-map`
            );
            const seats = seatMapRes.data.data.seats || [];
            invStatusMap[event.id] = {
              initialized: seats.length > 0,
              count: seats.length,
            };
          } catch {
            invStatusMap[event.id] = { initialized: false, count: 0 };
          }
        })
      );
      setInventoryMap(invStatusMap);

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
      setInventoryMap((prev) => ({
        ...prev,
        [newEvent.id]: { initialized: false, count: 0 },
      }));
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

  async function handleInitializeInventory(eventId: number) {
    try {
      setInitializingEventId(eventId);
      setError("");
      setSuccess("");

      const res = await api.post<ApiResponse<ShowSeat[]>>(
        `/events/${eventId}/inventory/initialize`
      );

      const seats = res.data.data || [];
      setInventoryMap((prev) => ({
        ...prev,
        [eventId]: {
          initialized: seats.length > 0,
          count: seats.length,
        },
      }));

      setSuccess(
        `Inventory initialized successfully for event ID ${eventId} (${seats.length} seats created).`
      );
    } catch (err: any) {
      setError(
        err.response?.data?.message ||
          "Failed to initialize inventory for this event."
      );
    } finally {
      setInitializingEventId(null);
    }
  }

  async function handleDeleteEvent(event: EventResponse) {
    const confirmed = window.confirm(
      `Delete "${event.title}"? This cannot be undone. Events with existing bookings or waitlist entries cannot be deleted.`
    );
    if (!confirmed) return;

    try {
      setDeletingEventId(event.id);
      setError("");
      setSuccess("");

      await api.delete(`/events/${event.id}`);

      setEvents((prev) => prev.filter((item) => item.id !== event.id));
      setInventoryMap((prev) => {
        const next = { ...prev };
        delete next[event.id];
        return next;
      });
      setSuccess(`Event "${event.title}" deleted successfully.`);
    } catch (err: any) {
      setError(
        err.response?.data?.message || "Failed to delete event. Please try again."
      );
    } finally {
      setDeletingEventId(null);
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
              const invInfo = inventoryMap[event.id];
              const isInitializing = initializingEventId === event.id;
              const isDeleting = deletingEventId === event.id;

              return (
                <article key={event.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h3 className="truncate text-lg font-semibold text-white">{event.title}</h3>
                      <p className="mt-1 text-xs text-slate-500">Event ID: {event.id}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${status === "Upcoming" ? "bg-blue-500/10 text-blue-400" : "bg-slate-700 text-slate-300"}`}>
                      {status}
                    </span>
                  </div>

                  <div className="space-y-3 text-sm text-slate-300">
                    <div className="flex items-center gap-3"><CalendarDays size={16} className="text-blue-400" />{formatDate(event.start_time)}</div>
                    {event.end_time && <div className="flex items-center gap-3"><Clock size={16} className="text-blue-400" />Ends {formatDate(event.end_time)}</div>}
                    <div className="flex items-center gap-3"><MapPin size={16} className="text-blue-400" />{event.venue?.name ?? `Venue #${event.venue_id}`}</div>
                  </div>

                  {/* Inventory Status & Actions */}
                  <div className="border-t border-slate-800 pt-4">
                    {invInfo?.initialized ? (
                      <div className="flex items-center gap-2 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-900/40 rounded-lg p-3">
                        <CheckCircle2 size={16} className="shrink-0" />
                        <span>Inventory Initialized ({invInfo.count} seats)</span>
                      </div>
                    ) : (
                      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-amber-500/10 border border-amber-900/40 p-3 text-xs text-amber-300">
                        <div className="flex items-center gap-1.5 font-medium">
                          <AlertTriangle size={14} className="shrink-0" />
                          <span>Inventory Not Initialized</span>
                        </div>
                        <button
                          onClick={() => handleInitializeInventory(event.id)}
                          disabled={isInitializing}
                          className="flex items-center gap-1.5 rounded bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-500 disabled:opacity-50"
                        >
                          {isInitializing ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            <Layers size={14} />
                          )}
                          Initialize Inventory
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4">
                    <Link href={`/events/${event.id}`} className="inline-flex items-center gap-2 text-sm font-medium text-blue-400 hover:text-blue-300">
                      <Ticket size={16} /> View event details & seat map
                    </Link>

                    <button
                      onClick={() => handleDeleteEvent(event)}
                      disabled={isDeleting}
                      title="Events with existing bookings or waitlist entries cannot be deleted."
                      className="flex items-center gap-1.5 rounded-lg border border-red-900/60 bg-red-950/30 px-3 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-950/60 disabled:opacity-50"
                    >
                      {isDeleting ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                      Delete Event
                    </button>
                  </div>
                </article>
              );
            })}
          </section>
        )}
      </div>
    </DashboardShell>
  );
}

