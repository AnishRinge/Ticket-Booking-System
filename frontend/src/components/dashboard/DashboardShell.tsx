"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import type { User, UserRole } from "@/types";
import Sidebar from "./Sidebar";
import Header from "./Header";

interface DashboardShellProps {
  children: React.ReactNode;
  role: UserRole;
  title: string;
}

export default function DashboardShell({
  children,
  role,
  title,
}: DashboardShellProps) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const currentUser = await getCurrentUser();

        if (currentUser.role !== role) {
          router.replace(`/dashboard`);
          return;
        }

        setUser(currentUser);
      } catch {
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [role, router]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Loading dashboard...
      </main>
    );
  }

  if (!user) return null;

  return (
    <div className="flex min-h-screen bg-slate-950">
      <Sidebar role={role} />

      <div className="min-w-0 flex-1">
        <Header user={user} title={title} />

        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}