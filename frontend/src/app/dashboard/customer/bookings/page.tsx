"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Ticket } from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import api from "@/lib/api";
import type { ApiResponse, BookingList } from "@/types";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function CustomerBookingsPage() {
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

  return (
    <DashboardShell role="CUSTOMER" title="My Bookings">
      <div className="space-y-6">
        <Link
          href="/dashboard/customer"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
        >
          <ArrowLeft size={16} />
          Back to dashboard
        </Link>

        <div>
          <h2 className="text-2xl font-semibold text-white">
            Booking history
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            View your confirmed and cancelled bookings.
          </p>
        </div>

        {loading ? (
          <div className="flex min-h-64 items-center justify-center text-slate-400">
            Loading bookings...
          </div>
        ) : !bookings?.items.length ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900 px-6 py-16 text-center">
            <Ticket className="mx-auto text-slate-600" size={36} />
            <h3 className="mt-4 font-medium text-white">
              No bookings found
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Your bookings will appear here after you make a reservation.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-5 py-4">Reference</th>
                    <th className="px-5 py-4">Date</th>
                    <th className="px-5 py-4">Status</th>
                    <th className="px-5 py-4 text-right">Amount</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-800">
                  {bookings.items.map((booking) => (
                    <tr key={booking.id}>
                      <td className="px-5 py-4 font-medium text-white">
                        <Link
                          href={`/bookings/${booking.id}`}
                          className="text-indigo-400 hover:text-indigo-300"
                        >
                          {booking.booking_reference}
                        </Link>
                      </td>

                      <td className="px-5 py-4 text-slate-400">
                        {formatDate(booking.created_at)}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                            booking.status === "CONFIRMED"
                              ? "bg-emerald-500/10 text-emerald-400"
                              : "bg-red-500/10 text-red-400"
                          }`}
                        >
                          {booking.status}
                        </span>
                      </td>

                      <td className="px-5 py-4 text-right font-medium text-white">
                        ₹{booking.total_price.toLocaleString("en-IN")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </DashboardShell>
  );
}