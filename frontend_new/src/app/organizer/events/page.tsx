"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Plus, Bot, Calendar, Users, ChevronRight, Search } from "lucide-react";
import { toast } from "sonner";
import { listEvents } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event } from "@/types";
import Button from "@/components/ui/Button";
import { EventStatusBadge, EventStageBadge } from "@/components/ui/Badge";

function EmptyState() {
  const router = useRouter();
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "1.5rem",
        padding: "6rem 0",
        textAlign: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          height: "5rem",
          width: "5rem",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "1rem",
          background: "rgba(232,80,58,0.1)",
          border: "1px solid rgba(232,80,58,0.2)",
        }}
      >
        <Calendar size={40} color="#e8503a" />
      </div>
      <div>
        <h3
          style={{
            fontSize: "1.25rem",
            fontWeight: 700,
            color: "#fff",
            margin: 0,
          }}
        >
          No events yet
        </h3>
        <p
          style={{
            marginTop: "0.5rem",
            fontSize: "0.875rem",
            color: "rgba(255,255,255,0.4)",
            maxWidth: "24rem",
          }}
        >
          Create your first event manually or let our AI assistant guide you
          through the setup process.
        </p>
      </div>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", justifyContent: "center" }}>
        <Button
          variant="primary"
          onClick={() => router.push("/organizer/events/create")}
        >
          <Plus size={16} /> Create Event
        </Button>
        <Button
          variant="secondary"
          onClick={() => router.push("/organizer/ai-create")}
        >
          <Bot size={16} /> AI Create
        </Button>
      </div>
    </motion.div>
  );
}

export default function OrganizerEventsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchFocus, setSearchFocus] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    listEvents()
      .then(setEvents)
      .catch((err: Error) =>
        toast.error(err.message || "Failed to load events")
      )
      .finally(() => setLoading(false));
  }, [authLoading, user]);

  const filtered = events.filter((e) =>
    e.name.toLowerCase().includes(search.toLowerCase())
  );

  const gridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
    gap: "1rem",
  };

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <div
        style={{
          marginBottom: "2rem",
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.875rem",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#fff",
              margin: 0,
            }}
          >
            My Events
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            {events.length} event{events.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <Button
            variant="secondary"
            onClick={() => router.push("/organizer/ai-create")}
          >
            <Bot size={16} /> AI Create
          </Button>
          <Button
            variant="primary"
            onClick={() => router.push("/organizer/events/create")}
          >
            <Plus size={16} /> Create Event
          </Button>
        </div>
      </div>

      {events.length > 0 && (
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
              boxShadow: searchFocus ? "0 0 0 3px rgba(232,80,58,0.15)" : "none",
              transition: "all 0.2s",
              fontFamily: "inherit",
              boxSizing: "border-box",
            }}
          />
        </div>
      )}

      {loading && (
        <div style={gridStyle}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{
                height: "12rem",
                borderRadius: "0.75rem",
                border: "1px solid #222",
              }}
            />
          ))}
        </div>
      )}

      {!loading && filtered.length === 0 && events.length === 0 && (
        <EmptyState />
      )}

      {!loading && events.length > 0 && filtered.length === 0 && (
        <div
          style={{
            padding: "4rem 0",
            textAlign: "center",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          No events match &quot;{search}&quot;
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div style={gridStyle}>
          {filtered.map((event, i) => (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              style={{
                borderRadius: "0.75rem",
                border: "1px solid #222",
                background: "#111",
                padding: "1.5rem",
                display: "flex",
                flexDirection: "column",
              }}
              className="card-glow"
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  marginBottom: "1rem",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.375rem",
                  }}
                >
                  <EventStatusBadge status={event.status} />
                  <EventStageBadge stage={event.stage} />
                </div>
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.3)",
                  }}
                >
                  #{event.hash?.slice(0, 6)}
                </span>
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
                  fontSize: "0.75rem",
                  fontWeight: 500,
                  color: "#e8503a",
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
                  gap: "1rem",
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
                  <span>{event.max_participants} max</span>
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
                    <span>
                      {new Date(event.created_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
                <Link
                  href={`/organizer/events/${event.id}`}
                  style={{
                    marginLeft: "auto",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.25rem",
                    fontSize: "0.75rem",
                    color: "#e8503a",
                    fontWeight: 500,
                  }}
                >
                  Manage <ChevronRight size={14} />
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
