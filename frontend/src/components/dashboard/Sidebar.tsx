"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  CalendarDays,
  LayoutDashboard,
  LogOut,
  Map,
  Ticket,
  Users,
  Building2,
} from "lucide-react";
import { logout } from "@/lib/auth";
import type { UserRole } from "@/types";

interface SidebarProps {
  role: UserRole;
}

const navigation = {
  CUSTOMER: [
    { label: "Overview", href: "/dashboard/customer", icon: LayoutDashboard },
    { label: "Bookings", href: "/dashboard/customer/bookings", icon: Ticket },
  ],
  ORGANISER: [
    { label: "Overview", href: "/dashboard/organiser", icon: LayoutDashboard },
    { label: "Events", href: "/dashboard/organiser/events", icon: CalendarDays },
    { label: "Analytics", href: "/dashboard/organiser/analytics", icon: BarChart3 },
  ],
  ADMIN: [
    { label: "Overview", href: "/dashboard/admin", icon: LayoutDashboard },
    { label: "Venues", href: "/dashboard/admin/venues", icon: Building2 },
    { label: "Layouts", href: "/dashboard/admin/layouts", icon: Map },
    { label: "Users", href: "/dashboard/admin/users", icon: Users },
  ],
};

export default function Sidebar({ role }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  const items = navigation[role];

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950">
      <div className="border-b border-slate-800 px-6 py-6">
        <div className="text-lg font-bold text-white">TicketFlow</div>
        <div className="mt-1 text-xs uppercase tracking-wider text-slate-500">
          {role.toLowerCase()} portal
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {items.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href ||
            (item.href !== `/dashboard/${role.toLowerCase()}` &&
              pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                active
                  ? "bg-blue-600/15 text-blue-400"
                  : "text-slate-400 hover:bg-slate-900 hover:text-white"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 p-4">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400 transition hover:bg-red-950/30 hover:text-red-400"
        >
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </aside>
  );
}