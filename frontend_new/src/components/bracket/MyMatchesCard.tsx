"use client";

import { useCallback, useEffect, useState } from "react";
import { GitBranch, ExternalLink, Clock } from "lucide-react";
import { getMyMatches, type MyMatch } from "@/lib/api";
import { useEventStream } from "@/lib/useEventStream";

/**
 * The participant's "my match" card (Task 3, 5c): opponent, scheduled time, and
 * the join link for each of their bracket matches. Self-contained — fetches its
 * own data and renders nothing when the event has no bracket, so it's safe to drop
 * onto the participant event page unconditionally.
 */
export default function MyMatchesCard({ eventId }: { eventId: string }) {
  const [matches, setMatches] = useState<MyMatch[]>([]);

  const load = useCallback(() => {
    if (!eventId) return;
    getMyMatches(eventId).then(setMatches).catch(() => setMatches([]));
  }, [eventId]);

  useEffect(() => { load(); }, [load]);
  useEventStream(["bracket"], load); // live: opponent/time/link/result updates

  if (!matches.length) return null;

  const fmtTime = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "TBD";

  return (
    <div style={{ borderRadius: "0.75rem", border: "1px solid #222", background: "#111", padding: "1.25rem", marginBottom: "1.5rem" }}>
      <h3 style={{ margin: "0 0 0.75rem", fontSize: "1rem", fontWeight: 700, color: "#fff", display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <GitBranch size={18} color="#e8503a" /> Your Matches
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        {matches.map((m) => {
          const won = m.winner_team_id != null && m.status === "completed";
          return (
            <div key={m.match_id} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem",
              padding: "0.6rem 0.85rem", borderRadius: "0.5rem", background: "rgba(255,255,255,0.03)", border: "1px solid #1e1e1e",
            }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "#fff", fontWeight: 600 }}>
                  {m.round_number ? `Round ${m.round_number} · ` : ""}vs {m.opponent}
                </p>
                <p style={{ margin: "0.2rem 0 0", fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                  <Clock size={11} /> {fmtTime(m.scheduled_at)}
                  {m.status === "completed" && <span style={{ marginLeft: "0.4rem", color: won ? "#4ade80" : "#f87171" }}>· {won ? "result in" : "done"}</span>}
                </p>
              </div>
              {m.match_link && m.status !== "completed" && (
                <a href={m.match_link} target="_blank" rel="noopener noreferrer"
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", fontSize: "0.78rem", fontWeight: 700, color: "#e8503a", textDecoration: "none", flexShrink: 0 }}>
                  Join <ExternalLink size={13} />
                </a>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
