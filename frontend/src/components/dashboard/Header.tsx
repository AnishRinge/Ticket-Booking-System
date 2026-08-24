"use client";

import type { User } from "@/types";

interface HeaderProps {
  user: User;
  title: string;
}

export default function Header({ user, title }: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 py-4 backdrop-blur">
      <div>
        <h1 className="text-xl font-semibold text-white">{title}</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Manage your ticket booking activity
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium text-white">{user.full_name}</p>
          <p className="text-xs text-slate-500">{user.email}</p>
        </div>

        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600/20 text-sm font-semibold text-blue-400">
          {user.full_name.charAt(0).toUpperCase()}
        </div>
      </div>
    </header>
  );
}