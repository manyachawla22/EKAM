"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, LayoutDashboard, Zap, ShieldAlert } from "lucide-react";
import { signOut, auth } from "@/lib/firebase";
import { useAuth } from "@/lib/auth-context";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { getRoleDashboard } from "@/lib/api";
import { toast } from "sonner";
import NotificationsBell from "@/components/layout/NotificationsBell";

const roleBadgeVariant = {
  organizer: "warning" as const,
  participant: "info" as const,
  judge: "purple" as const,
  admin: "danger" as const,
};

export default function Navbar() {
  const { profile, loading, clearAuth } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      // Clear the EKAM JWT session (participants/judges have no Firebase user)
      clearAuth();
      // Firebase signOut is a no-op for OTP sessions but required for organizers
      await signOut(auth).catch(() => null);
      router.push("/");
      toast.success("Logged out successfully");
    } catch {
      toast.error("Failed to log out");
    }
  };

  return (
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="fixed top-0 left-0 right-0 z-40 border-b border-white/5 bg-[#0a0a0a]/80 backdrop-blur-xl"
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        {/* Logo */}
        <Link href="/" className="group flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#e8503a]">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="text-xl font-black italic tracking-tight text-white group-hover:text-[#e8503a] transition-colors">
            EKAM
          </span>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {loading ? (
            <div className="h-8 w-32 animate-pulse rounded-lg bg-white/5" />
          ) : profile ? (
            <>
              {/* User info */}
              <div className="hidden sm:flex items-center gap-2 text-sm">
                <span className="text-white/60">
                  {profile.name || profile.email}
                </span>
                <Badge variant={roleBadgeVariant[profile.role] || "default"}>
                  {profile.role}
                </Badge>
              </div>

              {/* Notifications */}
              <NotificationsBell />

              {/* Judge-only: private flagged-evaluations page */}
              {profile.role === "judge" && (
                <Link href="/judge/anomalies">
                  <Button variant="ghost" size="sm">
                    <ShieldAlert className="h-4 w-4" />
                    <span className="hidden sm:inline">Anomalies</span>
                  </Button>
                </Link>
              )}

              {/* Dashboard link */}
              <Link href={getRoleDashboard(profile.role)}>
                <Button variant="secondary" size="sm">
                  <LayoutDashboard className="h-4 w-4" />
                  <span className="hidden sm:inline">Dashboard</span>
                </Button>
              </Link>

              {/* Logout */}
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </>
          ) : (
            <>
              <Link href="/login">
                <Button variant="secondary" size="sm">
                  Login
                </Button>
              </Link>
              <Link href="/signup">
                <Button variant="primary" size="sm">
                  Sign Up
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </motion.nav>
  );
}
