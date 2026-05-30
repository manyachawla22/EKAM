"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Star, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { getMe, listEvents, listJudges } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event, Judge } from "@/types";
import Navbar from "@/components/layout/Navbar";
import { EventStatusBadge } from "@/components/ui/Badge";

interface AssignmentRow {
  event: Event;
  judge: Judge;
}

export default function JudgeAssignmentsPage() {
  const { user, loading: authLoading } = useAuth();
  const [rows, setRows] = useState<AssignmentRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const me = await getMe();
        const events = await listEvents().catch(() => []);
        const all: AssignmentRow[] = [];
        // Judge records are event-scoped and identified by email — there's no
        // FK from Judge → User. Match the judge's User email against each
        // event's Judge rows.
        const myEmail = (me.email || "").toLowerCase();
        for (const ev of events) {
          const eventJudges = await listJudges(ev.id).catch(() => []);
          for (const j of eventJudges) {
            if ((j.email || "").toLowerCase() === myEmail) {
              all.push({ event: ev, judge: j });
            }
          }
        }
        setRows(all);
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Failed to load assignments"
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [authLoading, user]);

  const pageWrap: React.CSSProperties = {
    minHeight: "100vh",
    background: "#0a0a0a",
  };
  const container: React.CSSProperties = {
    maxWidth: "56rem",
    margin: "0 auto",
    padding: "6rem 1.5rem 3rem",
  };

  return (
    <div style={pageWrap}>
      <Navbar />
      <div style={container}>
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
            My Assignments
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            Events you&apos;re assigned to judge
          </p>
        </div>

        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="shimmer"
                style={{ height: "5rem", borderRadius: "0.75rem" }}
              />
            ))}
          </div>
        ) : rows.length === 0 ? (
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
              <Star size={32} color="rgba(255,255,255,0.2)" />
            </div>
            <p style={{ color: "rgba(255,255,255,0.4)", margin: 0 }}>
              No assignments yet
            </p>
            <p
              style={{
                fontSize: "0.875rem",
                color: "rgba(255,255,255,0.3)",
                maxWidth: "26rem",
                margin: 0,
              }}
            >
              An organizer needs to add you to an event using your email
              ({user?.email}) before assignments appear here.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {rows.map(({ event, judge }, i) => (
              <motion.div
                key={`${event.id}-${judge.id}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  borderRadius: "0.75rem",
                  border: "1px solid #222",
                  background: "#111",
                  padding: "1.25rem",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    height: "2.75rem",
                    width: "2.75rem",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "0.75rem",
                    background: "rgba(168,85,247,0.15)",
                    color: "#c084fc",
                    flexShrink: 0,
                  }}
                >
                  <Star size={20} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.5rem",
                      flexWrap: "wrap",
                    }}
                  >
                    <h3
                      style={{
                        fontWeight: 600,
                        color: "#fff",
                        margin: 0,
                        fontSize: "1rem",
                      }}
                    >
                      {event.name}
                    </h3>
                    <EventStatusBadge status={event.status} />
                  </div>
                  <p
                    style={{
                      marginTop: "0.25rem",
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.4)",
                      margin: 0,
                    }}
                  >
                    {event.type}
                    {judge.institution ? ` · ${judge.institution}` : ""}
                  </p>
                </div>
                <Link
                  href={`/organizer/events/${event.id}/submissions`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.25rem",
                    fontSize: "0.875rem",
                    color: "#e8503a",
                  }}
                >
                  Submissions <ChevronRight size={16} />
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
