"use client";

export const dynamic = "force-dynamic";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getRoleDashboard } from "@/lib/api";
import { Zap } from "lucide-react";

export default function DashboardPage() {
  const { profile, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (profile) {
        router.replace(getRoleDashboard(profile.role));
      } else {
        router.replace("/login");
      }
    }
  }, [loading, profile, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
      <div className="flex flex-col items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-[#e8503a] animate-pulse">
          <Zap className="h-7 w-7 text-white" />
        </div>
        <p className="text-sm text-white/40">Redirecting to your dashboard...</p>
      </div>
    </div>
  );
}
