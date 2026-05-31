"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Users, Crown, X } from "lucide-react";
import { listTeams } from "@/lib/api";
import type { Team } from "@/types";

interface Props {
  open: boolean;
  onClose: () => void;
  eventId: string;
  teamId: string;
  teamName: string;
  /** Pass the already-loaded Team object to skip the fetch. */
  initialTeam?: Team;
}

export default function TeamDetailModal({
  open,
  onClose,
  eventId,
  teamId,
  teamName,
  initialTeam,
}: Props) {
  const [team, setTeam] = useState<Team | null>(initialTeam ?? null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (initialTeam) { setTeam(initialTeam); return; }
    if (team) return;
    setLoading(true);
    listTeams(eventId)
      .then((teams) => setTeam(teams.find((t) => t.id === teamId) ?? null))
      .catch(() => setTeam(null))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  const members = team?.members ?? [];

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.55)",
              zIndex: 50,
            }}
          />

          {/* Modal */}
          <motion.div
            key="modal"
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 16 }}
            transition={{ type: "spring", stiffness: 320, damping: 26 }}
            style={{
              position: "fixed",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: "min(22rem, calc(100vw - 2rem))",
              borderRadius: "1rem",
              border: "1px solid #222",
              background: "#111",
              boxShadow: "0 20px 60px rgba(0,0,0,0.7)",
              zIndex: 51,
              overflow: "hidden",
            }}
          >
            {/* Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "1rem 1.25rem",
                borderBottom: "1px solid #1a1a1a",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                <div
                  style={{
                    display: "flex",
                    height: "2rem",
                    width: "2rem",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "0.5rem",
                    background: "rgba(232,80,58,0.12)",
                    color: "#e8503a",
                    flexShrink: 0,
                  }}
                >
                  <Users size={14} />
                </div>
                <span style={{ fontWeight: 700, color: "#fff", fontSize: "0.95rem" }}>
                  {teamName}
                </span>
              </div>
              <button
                onClick={onClose}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "rgba(255,255,255,0.4)",
                  display: "flex",
                  padding: "0.25rem",
                  borderRadius: "0.375rem",
                  transition: "color 0.15s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#fff")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(255,255,255,0.4)")}
              >
                <X size={16} />
              </button>
            </div>

            {/* Body */}
            <div style={{ padding: "1rem 1.25rem" }}>
              {loading ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div
                      key={i}
                      className="shimmer"
                      style={{ height: "2.5rem", borderRadius: "0.5rem" }}
                    />
                  ))}
                </div>
              ) : members.length === 0 ? (
                <p
                  style={{
                    color: "rgba(255,255,255,0.3)",
                    fontSize: "0.875rem",
                    textAlign: "center",
                    padding: "1.25rem 0",
                    margin: 0,
                  }}
                >
                  No members assigned to this team yet.
                </p>
              ) : (
                <>
                  <p
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      color: "rgba(255,255,255,0.3)",
                      margin: "0 0 0.75rem",
                    }}
                  >
                    {members.length} member{members.length !== 1 ? "s" : ""}
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {members.map((m) => {
                      const name =
                        m.participant?.name ||
                        m.user?.name ||
                        m.participant?.email ||
                        `Member ${String(m.participant_id).slice(0, 8)}`;
                      const email = m.participant?.email || m.user?.email || null;
                      const institution = m.participant?.institution || null;
                      return (
                        <div
                          key={m.id}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.625rem",
                            padding: "0.625rem 0.75rem",
                            borderRadius: "0.5rem",
                            background: m.is_leader
                              ? "rgba(250,204,21,0.06)"
                              : "rgba(255,255,255,0.03)",
                            border: m.is_leader
                              ? "1px solid rgba(250,204,21,0.15)"
                              : "1px solid #1a1a1a",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              height: "1.75rem",
                              width: "1.75rem",
                              alignItems: "center",
                              justifyContent: "center",
                              borderRadius: "9999px",
                              background: "rgba(255,255,255,0.06)",
                              color: "rgba(255,255,255,0.5)",
                              flexShrink: 0,
                              fontSize: "0.7rem",
                              fontWeight: 700,
                            }}
                          >
                            {name.charAt(0).toUpperCase()}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <p
                              style={{
                                margin: 0,
                                fontSize: "0.875rem",
                                color: "#fff",
                                fontWeight: m.is_leader ? 600 : 400,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {name}
                            </p>
                            {email && (
                              <a
                                href={`mailto:${email}`}
                                onClick={(e) => e.stopPropagation()}
                                style={{
                                  display: "block",
                                  fontSize: "0.72rem",
                                  color: "rgba(99,102,241,0.8)",
                                  textDecoration: "none",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                {email}
                              </a>
                            )}
                            {institution && (
                              <p
                                style={{
                                  margin: 0,
                                  fontSize: "0.7rem",
                                  color: "rgba(255,255,255,0.35)",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                {institution}
                              </p>
                            )}
                          </div>
                          {m.is_leader && (
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "0.25rem",
                                fontSize: "0.65rem",
                                fontWeight: 700,
                                color: "#facc15",
                              }}
                            >
                              <Crown size={11} />
                              Leader
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
