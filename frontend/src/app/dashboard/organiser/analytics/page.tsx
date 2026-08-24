"use client";

import { useEffect, useState } from "react";
import { BarChart3, IndianRupee, Ticket, CalendarDays } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import DashboardShell from "@/components/dashboard/DashboardShell";
import StatCard from "@/components/dashboard/StatCard";
import api from "@/lib/api";
import type { ApiResponse, OrganiserDashboard } from "@/types";

export default function OrganiserAnalyticsPage() {
  const [data, setData] = useState<OrganiserDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadAnalytics() {
      try {
        const response = await api.get<ApiResponse<OrganiserDashboard>>("/dashboard/organiser");
        setData(response.data.data);
      } catch {
        setError("Unable to load organiser analytics.");
      } finally {
        setLoading(false);
      }
    }

    loadAnalytics();
  }, []);

  return (
    <DashboardShell role="ORGANISER" title="Analytics">
      {loading ? (
        <div className="flex min-h-64 items-center justify-center text-slate-400">Loading analytics...</div>
      ) : error ? (
        <div className="rounded-xl border border-red-900 bg-red-950/30 p-6 text-red-300">{error}</div>
      ) : data ? (
        <div className="space-y-6">
          <section>
            <h2 className="text-2xl font-semibold text-white">Performance analytics</h2>
            <p className="mt-1 text-sm text-slate-500">Confirmed booking and revenue metrics from your organiser dashboard.</p>
          </section>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total events" value={data.total_events} icon={CalendarDays} />
            <StatCard label="Confirmed bookings" value={data.total_bookings} icon={Ticket} />
            <StatCard label="Total revenue" value={`₹${data.total_revenue.toLocaleString("en-IN")}`} icon={IndianRupee} />
            <StatCard label="Average booking value" value={data.total_bookings ? `₹${Math.round(data.total_revenue / data.total_bookings).toLocaleString("en-IN")}` : "₹0"} icon={BarChart3} />
          </section>

          <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <h3 className="font-semibold text-white">Bookings and revenue by event</h3>
            <p className="mt-1 text-xs text-slate-500">Values reflect confirmed bookings returned by the organiser API.</p>
            {data.recent_events.length === 0 ? (
              <div className="flex h-64 items-center justify-center text-sm text-slate-500">No event analytics available.</div>
            ) : (
              <div className="mt-5 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.recent_events}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="title" tick={{ fill: "#64748b", fontSize: 11 }} />
                    <YAxis yAxisId="bookings" allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} />
                    <YAxis yAxisId="revenue" orientation="right" tick={{ fill: "#64748b", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }} />
                    <Bar yAxisId="bookings" dataKey="bookings_count" name="Bookings" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="revenue" dataKey="revenue" name="Revenue" fill="#22c55e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}
