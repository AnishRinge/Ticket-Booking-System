"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  Armchair,
  Check,
  Layers,
  Loader2,
  Map,
  Plus,
  Trash2,
} from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import api from "@/lib/api";
import type { ApiResponse, Seat, SeatCategory, Venue } from "@/types";

interface VenueLayout extends Venue {
  seats: Seat[];
}

export default function AdminLayoutsPage() {
  const [layouts, setLayouts] = useState<VenueLayout[]>([]);
  const [categories, setCategories] = useState<SeatCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Category Form State
  const [catName, setCatName] = useState("");
  const [catDesc, setCatDesc] = useState("");
  const [catSaving, setCatSaving] = useState(false);

  // Batch Seat Builder State
  const [selectedVenueId, setSelectedVenueId] = useState<number | "">("");
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | "">("");
  const [rowsInput, setRowsInput] = useState("A, B, C");
  const [startSeat, setStartSeat] = useState(1);
  const [endSeat, setEndSeat] = useState(10);
  const [seatsSaving, setSeatsSaving] = useState(false);
  const [deletingSeatId, setDeletingSeatId] = useState<number | null>(null);

  async function loadData() {
    try {
      setLoading(true);
      const [venuesRes, categoriesRes] = await Promise.all([
        api.get<ApiResponse<Venue[]>>("/venues"),
        api.get<ApiResponse<SeatCategory[]>>("/venues/categories"),
      ]);

      const fetchedCategories = categoriesRes.data.data;
      setCategories(fetchedCategories);

      if (fetchedCategories.length > 0 && selectedCategoryId === "") {
        const standardCat = fetchedCategories.find(
          (c) => c.name.toLowerCase() === "standard"
        );
        setSelectedCategoryId(standardCat ? standardCat.id : fetchedCategories[0].id);
      }

      const fetchedVenues = venuesRes.data.data;
      if (fetchedVenues.length > 0 && selectedVenueId === "") {
        setSelectedVenueId(fetchedVenues[0].id);
      }

      const loadedLayouts = await Promise.all(
        fetchedVenues.map(async (venue) => {
          const seatsRes = await api.get<ApiResponse<Seat[]>>(
            `/venues/${venue.id}/seats`
          );
          return { ...venue, seats: seatsRes.data.data };
        })
      );

      setLayouts(loadedLayouts);
      setError("");
    } catch {
      setError("Unable to load venue layouts and seat categories.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleCreateCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!catName.trim()) return;

    try {
      setCatSaving(true);
      setError("");
      setSuccess("");

      const res = await api.post<ApiResponse<SeatCategory>>(
        "/venues/categories",
        {
          name: catName.trim(),
          description: catDesc.trim() || undefined,
        }
      );

      const newCategory = res.data.data;
      setCategories((prev) => [...prev, newCategory]);
      if (selectedCategoryId === "") {
        setSelectedCategoryId(newCategory.id);
      }

      setCatName("");
      setCatDesc("");
      setSuccess(`Category "${newCategory.name}" created successfully.`);
    } catch (err: any) {
      setError(
        err.response?.data?.message || "Failed to create seat category."
      );
    } finally {
      setCatSaving(false);
    }
  }

  function parseRows(input: string): string[] {
    const parts = input
      .split(",")
      .map((s: string) => s.trim().toUpperCase())
      .filter(Boolean);

    const result: string[] = [];
    for (const part of parts) {
      if (part.includes("-")) {
        const [start, end] = part.split("-").map((s: string) => s.trim());
        if (
          start &&
          end &&
          start.length === 1 &&
          end.length === 1 &&
          start <= end
        ) {
          const startCode = start.charCodeAt(0);
          const endCode = end.charCodeAt(0);
          for (let code = startCode; code <= endCode; code++) {
            result.push(String.fromCharCode(code));
          }
        } else {
          result.push(part);
        }
      } else {
        result.push(part);
      }
    }
    return Array.from(new Set(result));
  }

  const parsedRows = parseRows(rowsInput);
  const totalSeatsToGenerate =
    parsedRows.length * Math.max(0, endSeat - startSeat + 1);

  async function handleBatchCreateSeats(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedVenueId || !selectedCategoryId || parsedRows.length === 0) {
      setError("Please select a venue, a category, and specify valid rows.");
      return;
    }
    if (endSeat < startSeat || startSeat < 1) {
      setError("Seat numbers must be valid (start seat >= 1 and end seat >= start seat).");
      return;
    }

    try {
      setSeatsSaving(true);
      setError("");
      setSuccess("");

      let createdCount = 0;
      let skippedCount = 0;

      for (const row of parsedRows) {
        for (let num = startSeat; num <= endSeat; num++) {
          try {
            await api.post(`/venues/${selectedVenueId}/seats`, {
              category_id: Number(selectedCategoryId),
              row_identifier: row,
              seat_number: num,
            });
            createdCount++;
          } catch (err: any) {
            if (err.response?.status === 400) {
              skippedCount++;
            } else {
              throw err;
            }
          }
        }
      }

      // Refresh layout data
      const seatsRes = await api.get<ApiResponse<Seat[]>>(
        `/venues/${selectedVenueId}/seats`
      );
      setLayouts((prev) =>
        prev.map((venue) =>
          venue.id === Number(selectedVenueId)
            ? { ...venue, seats: seatsRes.data.data }
            : venue
        )
      );

      const targetVenue = layouts.find((v) => v.id === Number(selectedVenueId));
      setSuccess(
        `Added ${createdCount} physical seat(s) to ${
          targetVenue?.name || "venue"
        }.${skippedCount > 0 ? ` (${skippedCount} seat(s) already existed)` : ""}`
      );
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to batch create seats.");
    } finally {
      setSeatsSaving(false);
    }
  }

  async function handleDeleteSeat(venueId: number, seatId: number) {
    if (!window.confirm("Delete this physical seat?")) return;

    try {
      setDeletingSeatId(seatId);
      await api.delete(`/venues/seats/${seatId}`);
      setLayouts((prev) =>
        prev.map((venue) =>
          venue.id === venueId
            ? { ...venue, seats: venue.seats.filter((s) => s.id !== seatId) }
            : venue
        )
      );
      setSuccess("Physical seat deleted successfully.");
    } catch (err: any) {
      setError(
        err.response?.data?.message || "Unable to delete physical seat."
      );
    } finally {
      setDeletingSeatId(null);
    }
  }

  return (
    <DashboardShell role="ADMIN" title="Layouts">
      <div className="space-y-6">
        <section>
          <h2 className="text-2xl font-semibold text-white">
            Physical Seat Layouts & Management
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Create seat categories, batch construct physical seats, and view venue layouts.
          </p>
        </section>

        {error && (
          <p className="rounded-lg border border-red-900 bg-red-950/30 p-4 text-sm text-red-300">
            {error}
          </p>
        )}

        {success && (
          <p className="flex items-center gap-2 rounded-lg border border-emerald-900 bg-emerald-950/30 p-4 text-sm text-emerald-300">
            <Check size={16} />
            {success}
          </p>
        )}

        {/* Section 1: Seat Categories */}
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center gap-2 text-white">
            <Layers className="text-blue-400" size={20} />
            <h3 className="font-semibold">Seat Categories</h3>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Define seating tiers (e.g., Standard, VIP, Premium) used for seat pricing.
          </p>

          <form onSubmit={handleCreateCategory} className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <input
              value={catName}
              onChange={(e) => setCatName(e.target.value)}
              placeholder="Category Name (e.g. Standard, VIP)"
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              required
            />
            <input
              value={catDesc}
              onChange={(e) => setCatDesc(e.target.value)}
              placeholder="Description (Optional)"
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
            />
            <button
              disabled={catSaving}
              className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {catSaving ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Add Category
            </button>
          </form>

          <div className="mt-4 flex flex-wrap gap-2">
            {categories.map((cat) => (
              <span
                key={cat.id}
                className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs font-medium text-slate-300"
              >
                {cat.name} <span className="text-slate-500">(ID: {cat.id})</span>
              </span>
            ))}
            {!categories.length && (
              <p className="text-xs text-slate-500">No seat categories created yet.</p>
            )}
          </div>
        </section>

        {/* Section 2: Batch Seat Builder */}
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center gap-2 text-white">
            <Armchair className="text-blue-400" size={20} />
            <h3 className="font-semibold">Batch Physical Seat Builder</h3>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Generate physical rows and seats in bulk for a selected venue.
          </p>

          <form onSubmit={handleBatchCreateSeats} className="mt-4 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-slate-400">Target Venue</label>
                <select
                  value={selectedVenueId}
                  onChange={(e) => setSelectedVenueId(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  required
                >
                  <option value="" disabled>Select a venue</option>
                  {layouts.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} (ID: {v.id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400">Seat Category</label>
                <select
                  value={selectedCategoryId}
                  onChange={(e) => setSelectedCategoryId(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  required
                >
                  <option value="" disabled>Select a category</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name} (ID: {cat.id})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-slate-400">
                  Rows (e.g. A, B, C or A-C)
                </label>
                <input
                  value={rowsInput}
                  onChange={(e) => setRowsInput(e.target.value)}
                  placeholder="A, B, C"
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400">Start Seat #</label>
                <input
                  type="number"
                  min={1}
                  value={startSeat}
                  onChange={(e) => setStartSeat(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400">End Seat #</label>
                <input
                  type="number"
                  min={1}
                  value={endSeat}
                  onChange={(e) => setEndSeat(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  required
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg bg-slate-950 p-3 text-xs text-slate-400 border border-slate-800">
              <div>
                Will generate <span className="font-semibold text-white">{totalSeatsToGenerate}</span> physical seat(s):{" "}
                <span className="text-blue-400 font-mono">
                  Rows [{parsedRows.join(", ")}] ({startSeat} to {endSeat})
                </span>
              </div>

              <button
                disabled={seatsSaving || totalSeatsToGenerate <= 0}
                className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {seatsSaving ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Batch Create Seats
              </button>
            </div>
          </form>
        </section>

        {/* Section 3: Read-Only & Delete Layout Viewer */}
        {loading ? (
          <div className="flex min-h-48 items-center justify-center text-slate-400">
            <Loader2 className="animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            {layouts.map((venue) => {
              const rows = Array.from(
                new Set(venue.seats.map((seat) => seat.row_identifier))
              ).sort();

              return (
                <section
                  key={venue.id}
                  className="rounded-xl border border-slate-800 bg-slate-900 p-5"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <Map className="text-blue-400" size={20} />
                      <div>
                        <h3 className="font-semibold text-white">{venue.name}</h3>
                        <p className="text-sm text-slate-500">
                          {venue.address} ·{" "}
                          <span className="font-medium text-white">{venue.seats.length}</span> physical seats
                        </p>
                      </div>
                    </div>
                  </div>

                  {venue.seats.length ? (
                    <div className="mt-5 space-y-3">
                      {rows.map((row) => (
                        <div key={row} className="flex items-center gap-3">
                          <span className="w-6 text-sm font-semibold text-slate-400">
                            {row}
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {venue.seats
                              .filter((seat) => seat.row_identifier === row)
                              .sort((a, b) => a.seat_number - b.seat_number)
                              .map((seat) => {
                                const isDeleting = deletingSeatId === seat.id;
                                return (
                                  <div
                                    key={seat.id}
                                    className="group relative flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:border-slate-500"
                                    title={`${seat.category?.name ?? "Seat"} · Seat ID: ${seat.id}`}
                                  >
                                    <span>{seat.seat_number}</span>
                                    <button
                                      onClick={() => handleDeleteSeat(venue.id, seat.id)}
                                      disabled={isDeleting}
                                      className="ml-1 text-slate-500 hover:text-red-400"
                                      title="Delete seat"
                                    >
                                      {isDeleting ? (
                                        <Loader2 size={12} className="animate-spin" />
                                      ) : (
                                        <Trash2 size={12} />
                                      )}
                                    </button>
                                  </div>
                                );
                              })}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-5 text-sm text-slate-500">
                      No physical seats configured.
                    </p>
                  )}
                </section>
              );
            })}
            {!layouts.length && (
              <p className="text-sm text-slate-500">No venues found.</p>
            )}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}

