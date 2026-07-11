"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../contexts/AuthContext";
import { BookOpen, LayoutDashboard, MessageSquare, LogOut, User } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Chat Space", href: "/chat", icon: MessageSquare },
  ];

  return (
    <header className="relative z-40 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-tr from-indigo-600 to-blue-500 text-white font-bold text-base shadow-md shadow-indigo-500/20">
              RP
            </div>
            <span className="hidden text-base font-bold text-white sm:block tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              Research Assistant
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1 sm:gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                    isActive
                      ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                      : "text-slate-400 hover:text-slate-200 border border-transparent hover:bg-slate-900/50"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Profile and Actions */}
        <div className="flex items-center gap-4">
          {user && (
            <div className="hidden items-center gap-2 rounded-lg bg-slate-900/60 border border-slate-800/60 px-3 py-1.5 sm:flex">
              <div className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-500/20 text-indigo-400">
                <User className="h-3.5 w-3.5" />
              </div>
              <span className="text-xs font-medium text-slate-300">
                {user.full_name || user.email}
              </span>
            </div>
          )}

          <button
            onClick={logout}
            title="Log Out"
            className="flex items-center gap-2 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-950 hover:bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-all hover:shadow-inner active:scale-98"
          >
            <LogOut className="h-4 w-4 text-red-500" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
