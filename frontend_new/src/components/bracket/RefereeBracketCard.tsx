"use client";

import { useCallback, useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { toast } from "sonner";
import { getBracket, patchMatch, type Bracket, type BracketMatch } from "@/lib/api";
import { useEventStream } from "@/lib/useEventStream";

/**
 * Referee-facing bracket scoring for a tournament event. Shows the matches that
 * are ready to play and lets the evaluator enter each side's score — the higher
 * score wins and the tree advances (same backend path as the organizer bracket).
 * Renders nothing when the event has no bracket. Lives on the judge dashboard.
 */
export default function RefereeBracketCard({ eventId }: { eventId: string }) {
  const [bracket, setBracket] = useState<Bracket>({ rounds: [] });

  const refresh = useCallback(async () => {
    try {
      setBracket(await getBracket(eventId));
    } catch {
      /* no bracket / no access — render nothing */
    }
  }, [eventId]);

  useEffect(() => { refresh(); }, [refresh]);
  useEventStream(["bracket"], refresh);

  const hasMatches = bracket.rounds.some((r) => r.matches.length > 0);
  if (!hasMatches) return null;

  return (
    <div style={{ marginTop: "1rem", borderRadius: "0.75rem", border: "1px solid #222", background: "#0d0d0d", padding: "1rem" }}>
      <p style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", fontWeight: 700, color: "#fff", margin: "0 0 0.75rem" }}>
        <Trophy size={15} color="#e8503a" /> Score the bracket matches
      </p>
      <div style={{ display: "flex", gap: "1.25rem", overflowX: "auto", paddingBottom: "0.5rem" }}>
        {bracket.rounds.map((rnd) => (
          <div key={rnd.round_number} style={{ display: "flex", flexDirection: "column", gap: "0.75rem", minWidth: "13rem" }}>
            <p style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {rnd.round_number === bracket.rounds.length ? "Final" : `Round ${rnd.round_number}`}
            </p>
            {rnd.matches.map((m) => (
              <RefMatch key={m.id} m={m} onScored={setBracket} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function RefMatch({ m, onScored }: { m: BracketMatch; onScored: (b: Bracket) => void }) {
  const [sa, setSa] = useState(m.score_a != null ? String(m.score_a) : "");
  const [sb, setSb] = useState(m.score_b != null ? String(m.score_b) : "");
  const done = m.status === "completed";
  const ready = !!m.side_a.team_id && !!m.side_b.team_id;

  const row = (name: string, score: number | null, isWinner: boolean) => (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem",
      padding: "0.35rem 0.55rem", borderRadius: "0.4rem", fontSize: "0.8rem",
      background: isWinner ? "rgba(232,80,58,0.12)" : "rgba(255,255,255,0.03)",
      border: `1px solid ${isWinner ? "#e8503a" : "#1e1e1e"}`,
      color: isWinner ? "#fff" : "rgba(255,255,255,0.8)", fontWeight: isWinner ? 700 : 500,
    }}>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</span>
      <span style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
        {score != null && <span style={{ fontWeight: 700 }}>{score}</span>}
        {isWinner && <span style={{ fontSize: "0.7rem" }}>🏆</span>}
      </span>
    </div>
  );

  const submit = async () => {
    if (sa === "" || sb === "") return toast.error("Enter both scores.");
    const na = Number(sa), nb = Number(sb);
    if (na === nb) return toast.error("Scores are tied — a knockout needs a winner.");
    const winner = na > nb ? m.side_a.team_id : m.side_b.team_id;
    if (!winner) return;
    try {
      onScored(await patchMatch(m.id, { winner_team_id: winner, score_a: na, score_b: nb }));
      toast.success("Score recorded — winner advances.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to record score");
    }
  };

  const inp: React.CSSProperties = {
    borderRadius: "0.35rem", border: "1px solid #222", background: "#111",
    padding: "0.3rem 0.4rem", fontSize: "0.72rem", color: "#fff", outline: "none", width: "4.5rem",
  };

  return (
    <div style={{ borderRadius: "0.55rem", border: "1px solid #1e1e1e", background: "#111", padding: "0.6rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
      {row(m.side_a.name, m.score_a, m.winner_team_id === m.side_a.team_id)}
      {row(m.side_b.name, m.score_b, m.winner_team_id === m.side_b.team_id)}
      {!done && ready && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", marginTop: "0.1rem" }}>
          <input value={sa} onChange={(e) => setSa(e.target.value)} type="number" placeholder="A" style={inp} />
          <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.72rem" }}>vs</span>
          <input value={sb} onChange={(e) => setSb(e.target.value)} type="number" placeholder="B" style={inp} />
          <button onClick={submit} style={{ ...inp, width: "auto", flex: 1, cursor: "pointer", color: "#4ade80", fontWeight: 700, textAlign: "center" }}>
            Record
          </button>
        </div>
      )}
      {!ready && !done && (
        <p style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.3)", margin: 0 }}>Waiting for both contestants…</p>
      )}
    </div>
  );
}
