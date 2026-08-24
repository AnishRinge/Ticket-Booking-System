"use client";

import { FormEvent, useEffect, useState } from "react";
import { Building2, Loader2, Plus, Trash2 } from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import api from "@/lib/api";
import type { ApiResponse, Venue } from "@/types";

export default function AdminVenuesPage() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function loadVenues() {
    try {
      setLoading(true);
      const response = await api.get<ApiResponse<Venue[]>>("/venues");
      setVenues(response.data.data);
      setError("");
    } catch {
      setError("Unable to load venues.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadVenues();
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !address.trim()) return;

    try {
      setSaving(true);
      const response = await api.post<ApiResponse<Venue>>("/venues", {
        name: name.trim(),
        address: address.trim(),
      });
      setVenues((current) => [...current, response.data.data]);
      setName("");
      setAddress("");
      setError("");
    } catch {
      setError("Unable to create venue.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(venue: Venue) {
    if (!window.confirm(`Delete ${venue.name}?`)) return;

    try {
      await api.delete(`/venues/${venue.id}`);
      setVenues((current) => current.filter((item) => item.id !== venue.id));
    } catch {
      setError("Unable to delete venue. It may still be referenced by events or seats.");
    }
  }

  return (
    <DashboardShell role="ADMIN" title="Venues">
      <div className="space-y-6">
        <section>
          <h2 className="text-2xl font-semibold text-white">Venue management</h2>
          <p className="mt-1 text-sm text-slate-500">Manage real venues used by events.</p>
        </section>

        {error && <p className="rounded-lg border border-red-900 bg-red-950/30 p-4 text-sm text-red-300">{error}</p>}

        <form onSubmit={handleCreate} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h3 className="font-semibold text-white">Add venue</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Venue name" className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500" required />
            <input value={address} onChange={(event) => setAddress(event.target.value)} placeholder="Address" className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500" required />
            <button disabled={saving} className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Add venue
            </button>
          </div>
        </form>

        {loading ? <div className="flex min-h-48 items-center justify-center text-slate-400"><Loader2 className="animate-spin" /></div> : (
          <section className="grid gap-4 md:grid-cols-2">
            {venues.map((venue) => (
              <article key={venue.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex gap-3"><Building2 className="mt-1 text-blue-400" size={20} /><div><h3 className="font-semibold text-white">{venue.name}</h3><p className="mt-1 text-sm text-slate-400">{venue.address}</p></div></div>
                  <button onClick={() => handleDelete(venue)} title="Delete venue" className="text-slate-500 hover:text-red-400"><Trash2 size={18} /></button>
                </div>
                <p className="mt-4 text-xs text-slate-500">Venue ID: {venue.id}</p>
              </article>
            ))}
            {!venues.length && <p className="text-sm text-slate-500">No venues found.</p>}
          </section>
        )}
      </div>
    </DashboardShell>
  );
}
