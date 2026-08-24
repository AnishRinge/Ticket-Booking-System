"use client";

import { useEffect, useState } from "react";
import { Loader2, Map } from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import api from "@/lib/api";
import type { ApiResponse, Seat, Venue } from "@/types";

interface VenueLayout extends Venue {
  seats: Seat[];
}

export default function AdminLayoutsPage() {
  const [layouts, setLayouts] = useState<VenueLayout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadLayouts() {
      try {
        const venuesResponse = await api.get<ApiResponse<Venue[]>>("/venues");
        const loaded = await Promise.all(venuesResponse.data.data.map(async (venue) => {
          const seatsResponse = await api.get<ApiResponse<Seat[]>>(`/venues/${venue.id}/seats`);
          return { ...venue, seats: seatsResponse.data.data };
        }));
        setLayouts(loaded);
      } catch {
        setError("Unable to load venue layouts.");
      } finally {
        setLoading(false);
      }
    }

    loadLayouts();
  }, []);

  return (
    <DashboardShell role="ADMIN" title="Layouts">
      <div className="space-y-6">
        <section>
          <h2 className="text-2xl font-semibold text-white">Physical seat layouts</h2>
          <p className="mt-1 text-sm text-slate-500">Inspect the physical seats configured for each venue.</p>
        </section>
        {error && <p className="rounded-lg border border-red-900 bg-red-950/30 p-4 text-sm text-red-300">{error}</p>}
        {loading ? <div className="flex min-h-48 items-center justify-center text-slate-400"><Loader2 className="animate-spin" /></div> : (
          <div className="space-y-4">
            {layouts.map((venue) => {
              const rows = Array.from(new Set(venue.seats.map((seat) => seat.row_identifier))).sort();
              return <section key={venue.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <div className="flex items-center gap-3"><Map className="text-blue-400" size={20} /><div><h3 className="font-semibold text-white">{venue.name}</h3><p className="text-sm text-slate-500">{venue.address} · {venue.seats.length} physical seats</p></div></div>
                {venue.seats.length ? <div className="mt-5 space-y-3">{rows.map((row) => <div key={row} className="flex items-center gap-3"><span className="w-6 text-sm font-semibold text-slate-400">{row}</span><div className="flex flex-wrap gap-2">{venue.seats.filter((seat) => seat.row_identifier === row).sort((a, b) => a.seat_number - b.seat_number).map((seat) => <span key={seat.id} title={`${seat.category?.name ?? "Seat"} · physical seat ${seat.id}`} className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300">{seat.seat_number}</span>)}</div></div>)}</div> : <p className="mt-5 text-sm text-slate-500">No physical seats configured.</p>}
              </section>;
            })}
            {!layouts.length && <p className="text-sm text-slate-500">No venues found.</p>}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}
