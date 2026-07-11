"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../contexts/AuthContext";

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-slate-950">
      <div className="flex flex-col items-center gap-4">
        {/* Loading Spinner */}
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-800 border-t-indigo-500" />
        <p className="text-sm font-medium text-slate-400 animate-pulse-subtle">
          Redirecting to Research Paper Assistant...
          {/* Note: This is user-facing, so we can make it look sleek */}
        </p>
      </div>
    </div>
  );
}
