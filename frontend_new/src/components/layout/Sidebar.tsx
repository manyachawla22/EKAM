"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Calendar,
  Users,
  Trophy,
  BarChart2,
  Bot,
  Home,
  Send,
  Star,
  Layers,
  UserCheck,
  Menu,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  exact?: boolean;
}

function getNavItems(role: string | null, eventId?: string): NavItem[] {
  if (role === "organizer" || role === "admin") {
    const base: NavItem[] = [
      { label: "Events", href: "/organizer/events", icon: <Calendar size={16} /> },
      { label: "AI Create", href: "/organizer/ai-create", icon: <Bot size={16} /> },
      { label: "AI Events", href: "/organizer/ai-events", icon: <Star size={16} /> },
    ];
    if (eventId) {
      base.push(
        { label: "Overview", href: `/organizer/events/${eventId}`, icon: <Home size={16} />, exact: true },
        { label: "Rounds", href: `/organizer/events/${eventId}/rounds`, icon: <Layers size={16} /> },
        { label: "Participants", href: `/organizer/events/${eventId}/participants`, icon: <Users size={16} /> },
        { label: "Teams", href: `/organizer/events/${eventId}/teams`, icon: <Trophy size={16} /> },
        { label: "Judges", href: `/organizer/events/${eventId}/judges`, icon: <UserCheck size={16} /> },
        { label: "Submissions", href: `/organizer/events/${eventId}/submissions`, icon: <Send size={16} /> },
        { label: "Approvals", href: `/organizer/events/${eventId}/approvals`, icon: <ShieldCheck size={16} /> },
        { label: "Anomalies", href: `/organizer/events/${eventId}/anomalies`, icon: <AlertTriangle size={16} /> },
        { label: "Reports", href: `/organizer/events/${eventId}/reports`, icon: <BarChart2 size={16} /> }
      );
    }
    return base;
  }
  if (role === "participant")
    return [{ label: "Browse Events", href: "/participant/events", icon: <Calendar size={16} /> }];
  if (role === "judge")
    return [{ label: "My Assignments", href: "/judge/assignments", icon: <Star size={16} /> }];
  return [];
}

function extractEventId(pathname: string | null): string | undefined {
  if (!pathname) return undefined;
  const m = pathname.match(/^\/organizer\/events\/([0-9a-f-]{36})(?:\/|$)/i);
  return m?.[1];
}

const SIDEBAR_WIDTH = "15rem";

interface SidebarProps {
  eventId?: string;
}

export default function Sidebar({ eventId: eventIdProp }: SidebarProps = {}) {
  const { role } = useAuth();
  const pathname = usePathname();
  const eventId = eventIdProp ?? extractEventId(pathname);

  // Hidden by default on mobile (<=767px), open by default on desktop.
  // Persisted between routes via local storage so closing once stays closed.
  const [open, setOpen] = useState(true);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem("ekam:sidebar") : null;
    if (stored !== null) setOpen(stored === "1");
    else setOpen(window.innerWidth >= 768);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem("ekam:sidebar", open ? "1" : "0");
    // Drive the layout's left padding via a CSS variable so <main> shifts
    // with the sidebar instead of being covered by it.
    document.documentElement.style.setProperty(
      "--ekam-sb-width",
      open ? SIDEBAR_WIDTH : "0"
    );
  }, [open]);

  // Toggle is rendered globally; close on route change for mobile.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.innerWidth < 768) setOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const navItems = getNavItems(role, eventId);
  if (navItems.length === 0) return null;

  const isActive = (item: NavItem) =>
    item.exact ? pathname === item.href : pathname?.startsWith(item.href);

  const navLink = (item: NavItem) => {
    const active = isActive(item);
    return (
      <Link
        key={item.href}
        href={item.href}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          borderRadius: "0.5rem",
          padding: "0.625rem 0.75rem",
          fontSize: "0.875rem",
          fontWeight: 500,
          background: active ? "rgba(232,80,58,0.15)" : "transparent",
          color: active ? "#e8503a" : "rgba(255,255,255,0.65)",
          border: active
            ? "1px solid rgba(232,80,58,0.2)"
            : "1px solid transparent",
          textDecoration: "none",
          transition: "background 0.15s, color 0.15s",
        }}
      >
        <span style={{ flexShrink: 0, display: "flex" }}>{item.icon}</span>
        <span
          style={{
            overflow: "hidden",
            whiteSpace: "nowrap",
            textOverflow: "ellipsis",
          }}
        >
          {item.label}
        </span>
      </Link>
    );
  };

  return (
    <>
      {/* Toggle button — always visible, top-left under the navbar */}
      <button
        aria-label={open ? "Hide menu" : "Show menu"}
        onClick={() => setOpen((v) => !v)}
        style={{
          position: "fixed",
          top: "4.75rem",
          left: open ? `calc(${SIDEBAR_WIDTH} + 0.5rem)` : "0.5rem",
          zIndex: 35,
          display: "flex",
          height: "2.25rem",
          width: "2.25rem",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "0.5rem",
          background: "#111",
          color: "rgba(255,255,255,0.7)",
          border: "1px solid #222",
          cursor: "pointer",
          transition: "left 0.25s",
        }}
      >
        <Menu size={16} />
      </button>

      <aside
        style={{
          position: "fixed",
          left: 0,
          top: "4rem",
          bottom: 0,
          width: SIDEBAR_WIDTH,
          zIndex: 30,
          borderRight: "1px solid #222",
          background: "#0a0a0a",
          display: "flex",
          flexDirection: "column",
          overflowY: "auto",
          transform: open ? "translateX(0)" : `translateX(-100%)`,
          transition: "transform 0.25s",
        }}
      >
        <nav
          style={{
            flex: 1,
            padding: "1rem 0.625rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.25rem",
          }}
        >
          {navItems.map(navLink)}
        </nav>
      </aside>
    </>
  );
}
