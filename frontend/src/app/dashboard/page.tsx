"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import type { User } from "@/types";

export default function DashboardRedirect() {
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    async function redirectUser() {
      try {
        const user: User = await getCurrentUser();

        if (user.role === "ADMIN") {
          router.replace("/dashboard/admin");
        } else if (user.role === "ORGANISER") {
          router.replace("/dashboard/organiser");
        } else {
          router.replace("/dashboard/customer");
        }
      } catch {
        setError("Your session has expired. Please sign in again.");
        router.replace("/login");
      }
    }

    redirectUser();
  }, [router]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
        {error}
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
      Loading dashboard...
    </main>
  );
}