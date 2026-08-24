"use client";

import { useEffect, useState } from "react";
import { Loader2, Users } from "lucide-react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import api from "@/lib/api";
import type { ApiResponse, User } from "@/types";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadUsers() {
      try {
        const response = await api.get<ApiResponse<User[]>>("/users");
        setUsers(response.data.data);
      } catch {
        setError("Unable to load users.");
      } finally {
        setLoading(false);
      }
    }

    loadUsers();
  }, []);

  return (
    <DashboardShell role="ADMIN" title="Users">
      <div className="space-y-6">
        <section><h2 className="text-2xl font-semibold text-white">User directory</h2><p className="mt-1 text-sm text-slate-500">Review registered users and their roles.</p></section>
        {error && <p className="rounded-lg border border-red-900 bg-red-950/30 p-4 text-sm text-red-300">{error}</p>}
        {loading ? <div className="flex min-h-48 items-center justify-center text-slate-400"><Loader2 className="animate-spin" /></div> : <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900"><div className="flex items-center gap-3 border-b border-slate-800 p-5"><Users className="text-blue-400" size={20} /><h3 className="font-semibold text-white">{users.length} users</h3></div><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500"><tr><th className="px-5 py-4">Name</th><th className="px-5 py-4">Email</th><th className="px-5 py-4">Role</th></tr></thead><tbody className="divide-y divide-slate-800">{users.map((user) => <tr key={user.id}><td className="px-5 py-4 text-white">{user.full_name}</td><td className="px-5 py-4 text-slate-400">{user.email}</td><td className="px-5 py-4"><span className="rounded-full bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-400">{user.role}</span></td></tr>)}</tbody></table></div></section>}
      </div>
    </DashboardShell>
  );
}
