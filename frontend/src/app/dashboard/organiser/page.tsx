"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  CalendarDays,
  IndianRupee,
  Ticket,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import DashboardShell from "@/components/dashboard/DashboardShell";
import StatCard from "@/components/dashboard/StatCard";
import api from "@/lib/api";
import type { ApiResponse } from "@/types";

interface EventSummary {
  id: number;
  title: string;
  bookings_count: number;
  revenue: number;
  start_time: string;
  status: string;
}

interface OrganiserDashboard {
  total_events: number;
  total_bookings: number;
  total_revenue: number;
  recent_events: EventSummary[];
}

export default function OrganiserDashboardPage() {
  const [data, setData] = useState<OrganiserDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        const response = await api.get<ApiResponse<OrganiserDashboard>>(
          "/dashboard/organiser"
        );
        setData(response.data.data);
      } catch {
        setError("Unable to load organiser dashboard.");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  return (
    <DashboardShell role="ORGANISER" title="Organiser Dashboard">
      {loading ? (
        <div className="flex min-h-64 items-center justify-center text-slate-400">
          Loading dashboard...
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-900 bg-red-950/30 p-6 text-red-300">
          {error}
        </div>
      ) : data ? (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold text-white">
              Event overview
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Monitor your events, bookings and revenue.
            </p>
          </div>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Total events"
              value={data.total_events}
              icon={CalendarDays}
            />
            <StatCard
              label="Confirmed bookings"
              value={data.total_bookings}
              icon={Ticket}
            />
            <StatCard
              label="Total revenue"
              value={`₹${data.total_revenue.toLocaleString("en-IN")}`}
              icon={IndianRupee}
            />
            <StatCard
              label="Average booking value"
              value={
                data.total_bookings
                  ? `₹${Math.round(
                      data.total_revenue / data.total_bookings
                    ).toLocaleString("en-IN")}`
                  : "₹0"
              }
              icon={BarChart3}
            />
          </section>

          <section className="grid gap-6 xl:grid-cols-5">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 xl:col-span-3">
              <div className="mb-5">
                <h3 className="font-semibold text-white">
                  Bookings by event
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Confirmed bookings across your recent events
                </p>
              </div>

              {data.recent_events.length === 0 ? (
                <div className="flex h-64 items-center justify-center text-sm text-slate-500">
                  No event data available.
                </div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.recent_events}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis
                        dataKey="title"
                        tick={{ fill: "#64748b", fontSize: 11 }}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fill: "#64748b", fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#0f172a",
                          border: "1px solid #1e293b",
                          borderRadius: "8px",
                        }}
                      />
                      <Bar
                        dataKey="bookings_count"
                        name="Bookings"
                        fill="#3b82f6"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 xl:col-span-2">
              <div className="mb-5">
                <h3 className="font-semibold text-white">
                  Recent events
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Latest events under your account
                </p>
              </div>

              <div className="space-y-3">
                {data.recent_events.length === 0 ? (
                  <p className="py-10 text-center text-sm text-slate-500">
                    No events found.
                  </p>
                ) : (
                  data.recent_events.map((event) => (
                    <div
                      key={event.id}
                      className="rounded-lg border border-slate-800 bg-slate-950 p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium text-white">
                            {event.title}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            {new Date(event.start_time).toLocaleString()}
                          </p>
                        </div>

                        <span className="shrink-0 rounded-full bg-blue-500/10 px-2.5 py-1 text-xs text-blue-400">
                          {event.status}
                        </span>
                      </div>

                      <div className="mt-3 flex justify-between border-t border-slate-800 pt-3 text-xs">
                        <span className="text-slate-500">
                          {event.bookings_count} bookings
                        </span>
                        <span className="font-medium text-white">
                          ₹{event.revenue.toLocaleString("en-IN")}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}