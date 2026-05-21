"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { Loader2 } from "lucide-react";

export function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode, allowedRoles: string[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useAppStore();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;
    
    if (!user) {
      router.push("/auth");
      return;
    }

    if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
      // Redirect to appropriate dashboard
      if (user.role === "organizer") router.push("/dashboard");
      else if (user.role === "judge") router.push("/judge");
      else router.push("/portal/P-001");
    }
  }, [user, allowedRoles, router, isMounted, pathname]);

  if (!isMounted || !user || (allowedRoles.length > 0 && !allowedRoles.includes(user.role))) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
