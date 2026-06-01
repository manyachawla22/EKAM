"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Search, Calendar, Users, BookOpen, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { listEvents } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event } from "@/types";
import { EventStatusBadge, EventStageBadge } from "@/components/ui/Badge";
import Navbar from "@/components/layout/Navbar";

export default function ParticipantEventsPage() {
  const { profile, loading: authLoading } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchFocus, setSearchFocus] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!profile) {
      setLoading(false);
      return;
    }
    listEvents()
      .then((all) => setEvents(all.filter((e) => e.status === "active")))
      .catch((err: Error) =>
        toast.error(err.message || "Failed to load events")
      )
      .finally(() => setLoading(false));
  }, [authLoading, profile]);

  const filtered = events.filter(
    (e) =>
      e.name.toLowerCase().includes(search.toLowerCase()) ||
      e.type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a" }}>
      <Navbar />
      <div
        style={{
          maxWidth: "80rem",
          margin: "0 auto",
          padding: "6rem 1.5rem 3rem",
        }}
      >
        {/* Header */}
        <div style={{ marginBottom: "2rem" }}>
          <h1
            style={{
              fontSize: "1.875rem",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#fff",
              margin: 0,
            }}
          >
            Browse Events
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            Discover and join active events
          </p>
        </div>

        {/* Search */}
        <div
          style={{
            marginBottom: "1.5rem",
            position: "relative",
            maxWidth: "24rem",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: "0.875rem",
              top: "50%",
              transform: "translateY(-50%)",
              pointerEvents: "none",
              color: "rgba(255,255,255,0.3)",
              display: "flex",
            }}
          >
            <Search size={16} />
          </div>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onFocus={() => setSearchFocus(true)}
            onBlur={() => setSearchFocus(false)}
            placeholder="Search events..."
            style={{
              width: "100%",
              borderRadius: "0.5rem",
              border: `1px solid ${searchFocus ? "#e8503a" : "#222"}`,
              background: "#111",
              padding: "0.625rem 1rem 0.625rem 2.5rem",
              fontSize: "0.875rem",
              color: "#fff",
              outline: "none",
              boxShadow: searchFocus
                ? "0 0 0 3px rgba(232,80,58,0.15)"
                : "none",
              transition: "all 0.2s",
            }}
          />
        </div>

        {loading ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "1rem",
            }}
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="shimmer"
                style={{ height: "13rem", borderRadius: "0.75rem" }}
              />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "1rem",
              padding: "5rem 0",
              textAlign: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                height: "4rem",
                width: "4rem",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "1rem",
                background: "#111",
                border: "1px solid #222",
              }}
            >
              <BookOpen size={32} color="rgba(255,255,255,0.2)" />
            </div>
            <p style={{ color: "rgba(255,255,255,0.4)", margin: 0 }}>
              {search ? "No events match your search" : "No active events right now"}
            </p>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "1rem",
            }}
          >
            {filtered.map((event, i) => (
              <Link
                key={event.id}
                href={`/participant/events/${event.id}`}
                style={{ textDecoration: "none", color: "inherit" }}
              >
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -2, borderColor: "#333" }}
                transition={{ delay: i * 0.05 }}
                style={{
                  borderRadius: "0.75rem",
                  border: "1px solid #222",
                  background: "#111",
                  padding: "1.5rem",
                  display: "flex",
                  flexDirection: "column",
                  transition: "all 0.2s",
                  cursor: "pointer",
                  height: "100%",
                }}
              >
                <div
                  style={{
                    marginBottom: "1rem",
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                  }}
                >
                  <EventStatusBadge status={event.status} />
                  <EventStageBadge stage={event.stage} />
                </div>
                <h3
                  style={{
                    fontSize: "1.125rem",
                    fontWeight: 700,
                    color: "#fff",
                    margin: "0 0 0.25rem",
                  }}
                >
                  {event.name}
                </h3>
                <p
                  style={{
                    fontSize: "0.875rem",
                    color: "#e8503a",
                    fontWeight: 500,
                    margin: "0 0 0.75rem",
                  }}
                >
                  {event.type}
                </p>
                <p
                  style={{
                    fontSize: "0.875rem",
                    color: "rgba(255,255,255,0.4)",
                    flex: 1,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    margin: 0,
                  }}
                >
                  {event.description}
                </p>
                <div
                  style={{
                    marginTop: "1rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    borderTop: "1px solid #222",
                    paddingTop: "1rem",
                    flexWrap: "wrap",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.375rem",
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.4)",
                    }}
                  >
                    <Users size={14} />
                    <span>Max {event.max_participants}</span>
                  </div>
                  {event.created_at && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.375rem",
                        fontSize: "0.75rem",
                        color: "rgba(255,255,255,0.4)",
                      }}
                    >
                      <Calendar size={14} />
                      {new Date(event.created_at).toLocaleDateString()}
                    </div>
                  )}
                  <div
                    style={{
                      marginLeft: "auto",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.25rem",
                      fontSize: "0.75rem",
                      fontWeight: 500,
                      color: "#e8503a",
                    }}
                  >
                    Open Event
                    <ChevronRight size={14} />
                  </div>
                </div>
              </motion.div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
