"use client";

import { useEffect, useState } from "react";
import {
  Building2,
  CalendarDays,
  IndianRupee,
  Users,
} from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import StatCard from "@/components/dashboard/StatCard";
import api from "@/lib/api";
import type { ApiResponse } from "@/types";

interface RecentBooking {
  id: number;
  reference: string;
  user_email: string;
  event_title: string;
  status: string;
  total_price: number;
  created_at: string;
}

interface AdminDashboard {
  total_venues: number;
  total_events: number;
  total_revenue: number;
  total_users: number;
  recent_bookings: RecentBooking[];
}

export default function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        const response = await api.get<ApiResponse<AdminDashboard>>(
          "/dashboard/admin"
        );
        setData(response.data.data);
      } catch {
        setError("Unable to load admin dashboard.");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  return (
    <DashboardShell role="ADMIN" title="Admin Dashboard">
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
          <section>
            <h2 className="text-2xl font-semibold text-white">
              System overview
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Monitor the ticket booking platform.
            </p>
          </section>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Venues"
              value={data.total_venues}
              icon={Building2}
            />
            <StatCard
              label="Events"
              value={data.total_events}
              icon={CalendarDays}
            />
            <StatCard
              label="Users"
              value={data.total_users}
              icon={Users}
            />
            <StatCard
              label="Revenue"
              value={`₹${data.total_revenue.toLocaleString("en-IN")}`}
              icon={IndianRupee}
            />
          </section>

          <section className="rounded-xl border border-slate-800 bg-slate-900">
            <div className="border-b border-slate-800 px-5 py-4">
              <h3 className="font-semibold text-white">
                Recent bookings
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Latest booking activity across the platform
              </p>
            </div>

            {data.recent_bookings.length === 0 ? (
              <div className="px-5 py-12 text-center text-sm text-slate-500">
                No bookings found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="px-5 py-4">Reference</th>
                      <th className="px-5 py-4">Customer</th>
                      <th className="px-5 py-4">Event</th>
                      <th className="px-5 py-4">Status</th>
                      <th className="px-5 py-4">Date</th>
                      <th className="px-5 py-4 text-right">Amount</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-800">
                    {data.recent_bookings.map((booking) => (
                      <tr key={booking.id}>
                        <td className="px-5 py-4 font-medium text-white">
                          {booking.reference}
                        </td>

                        <td className="px-5 py-4 text-slate-400">
                          {booking.user_email}
                        </td>

                        <td className="px-5 py-4 text-slate-400">
                          {booking.event_title}
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                              booking.status === "CONFIRMED"
                                ? "bg-emerald-500/10 text-emerald-400"
                                : booking.status === "CANCELLED"
                                  ? "bg-red-500/10 text-red-400"
                                  : "bg-amber-500/10 text-amber-400"
                            }`}
                          >
                            {booking.status}
                          </span>
                        </td>

                        <td className="px-5 py-4 text-slate-500">
                          {new Date(booking.created_at).toLocaleString()}
                        </td>

                        <td className="px-5 py-4 text-right font-medium text-white">
                          ₹{booking.total_price.toLocaleString("en-IN")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}