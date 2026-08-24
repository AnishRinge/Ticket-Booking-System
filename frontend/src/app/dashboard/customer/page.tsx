"use client";

import { useEffect, useState } from "react";
import { CalendarDays, Clock3, Ticket, Wallet } from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import StatCard from "@/components/dashboard/StatCard";
import api from "@/lib/api";
import type { ApiResponse, BookingList } from "@/types";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function CustomerDashboard() {
  const [bookings, setBookings] = useState<BookingList | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadBookings() {
      try {
        const response = await api.get<BookingList>("/bookings/");
        setBookings(response.data);
      } finally {
        setLoading(false);
      }
    }

    loadBookings();
  }, []);

  const items = bookings?.items ?? [];
  const confirmed = items.filter((b) => b.status === "CONFIRMED");
  const cancelled = items.filter((b) => b.status === "CANCELLED");

  const totalSpent = confirmed.reduce(
    (sum, booking) => sum + booking.total_price,
    0
  );

  return (
    <DashboardShell role="CUSTOMER" title="Customer Dashboard">
      {loading ? (
        <div className="flex min-h-64 items-center justify-center text-slate-400">
          Loading your bookings...
        </div>
      ) : (
        <div className="space-y-6">
          <section>
            <h2 className="text-2xl font-semibold text-white">
              Welcome back
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Here&apos;s an overview of your ticket activity.
            </p>
                   <a
                     href="/events"
                     className="mt-4 inline-block rounded-lg bg-indigo-600 px-6 py-2 font-semibold text-white transition hover:bg-indigo-500"
                   >
                     Browse Events
                   </a>
          </section>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Total bookings"
              value={bookings?.total ?? 0}
              icon={Ticket}
            />
            <StatCard
              label="Confirmed"
              value={confirmed.length}
              icon={CalendarDays}
            />
            <StatCard
              label="Cancelled"
              value={cancelled.length}
              icon={Clock3}
            />
            <StatCard
              label="Total spent"
              value={`₹${totalSpent.toLocaleString("en-IN")}`}
              icon={Wallet}
            />
          </section>

          <section className="rounded-xl border border-slate-800 bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
              <div>
                <h3 className="font-semibold text-white">
                  Recent bookings
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Your latest booking activity
                </p>
              </div>

              <a
                href="/dashboard/customer/bookings"
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                View all
              </a>
            </div>

            {items.length === 0 ? (
              <div className="px-5 py-12 text-center text-sm text-slate-500">
                You don&apos;t have any bookings yet.
              </div>
            ) : (
              <div className="divide-y divide-slate-800">
                {items.slice(0, 5).map((booking) => (
                  <div
                    key={booking.id}
                    className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <p className="font-medium text-white">
                        {booking.booking_reference}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {formatDate(booking.created_at)}
                      </p>
                    </div>

                    <div className="flex items-center gap-4">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                          booking.status === "CONFIRMED"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {booking.status}
                      </span>

                      <span className="font-medium text-white">
                        ₹{booking.total_price.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}