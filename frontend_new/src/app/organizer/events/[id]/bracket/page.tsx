"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Trophy } from "lucide-react";
import {
  getBracket, generateBracket, patchMatch, listRounds,
  type Bracket, type BracketMatch, type BracketSide,
} from "@/lib/api";
import type { Round } from "@/types";
import { useEventStream } from "@/lib/useEventStream";
import Button from "@/components/ui/Button";

const card: React.CSSProperties = {
  borderRadius: "0.6rem", border: "1px solid #222", background: "#111", padding: "0.75rem",
  minWidth: "14rem", display: "flex", flexDirection: "column", gap: "0.4rem",
};
const sideBtn = (win: boolean, disabled: boolean): React.CSSProperties => ({
  display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem",
  padding: "0.4rem 0.6rem", borderRadius: "0.4rem", fontSize: "0.82rem", textAlign: "left",
  border: `1px solid ${win ? "#e8503a" : "#1e1e1e"}`,
  background: win ? "rgba(232,80,58,0.12)" : "rgba(255,255,255,0.03)",
  color: win ? "#fff" : "rgba(255,255,255,0.8)", fontWeight: win ? 700 : 500,
  cursor: disabled ? "default" : "pointer", width: "100%",
});
const inp: React.CSSProperties = {
  borderRadius: "0.35rem", border: "1px solid #222", background: "#0d0d0d",
  padding: "0.3rem 0.45rem", fontSize: "0.72rem", color: "#fff", outline: "none", flex: 1,
};

export default function BracketPage() {
  const { id } = useParams<{ id: string }>();
  const [bracket, setBracket] = useState<Bracket>({ rounds: [] });
  const [rounds, setRounds] = useState<Round[]>([]);
  const [roundId, setRoundId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!id) return;
    try {
      const [b, rs] = await Promise.all([getBracket(id), listRounds(id).catch(() => [] as Round[])]);
      setBracket(b);
      setRounds(rs);
      if (rs.length && !roundId) setRoundId(rs[rs.length - 1].id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load bracket");
    } finally {
      setLoading(false);
    }
  }, [id, roundId]);

  useEffect(() => { refresh(); }, [refresh]);
  // Live updates when any match result is recorded.
  useEventStream(["bracket", "pipeline"], refresh);

  const generate = async () => {
    if (!roundId) return toast.error("Pick a round to seed the bracket from.");
    setBusy(true);
    try {
      const res = await generateBracket(id, roundId, true);
      toast.success(res.skipped ? "Bracket already exists for that round." : `Bracket created (${res.created} matches).`);
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to generate");
    } finally {
      setBusy(false);
    }
  };

  const recordWinner = async (m: BracketMatch, winner: string | null) => {
    if (!winner) return;
    try {
      setBracket(await patchMatch(m.id, { winner_team_id: winner }));
      toast.success("Result recorded.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to record");
    }
  };

  // Record a refereed score for both sides; the higher score wins and the tree
  // advances. The scores are stored on the match and shown on the bracket.
  const recordScore = async (m: BracketMatch, sa: number, sb: number) => {
    if (sa === sb) return toast.error("Scores are tied — a knockout match needs a winner.");
    const winner = sa > sb ? m.side_a.team_id : m.side_b.team_id;
    if (!winner) return toast.error("Both contestants must be set before scoring.");
    try {
      setBracket(await patchMatch(m.id, { winner_team_id: winner, score_a: sa, score_b: sb }));
      toast.success("Score recorded — winner advances.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to record score");
    }
  };

  const saveLogistics = async (m: BracketMatch, link: string, time: string) => {
    try {
      setBracket(await patchMatch(m.id, {
        match_link: link || undefined,
        scheduled_at: time ? new Date(time).toISOString() : undefined,
      }));
      toast.success("Match updated.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    }
  };

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 900, fontStyle: "italic", color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Trophy size={22} color="#e8503a" /> Bracket
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <select value={roundId} onChange={(e) => setRoundId(e.target.value)} style={{ ...inp, flex: "none", fontSize: "0.8rem", padding: "0.45rem" }}>
            {rounds.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <Button variant="primary" loading={busy} onClick={generate}>Generate / seed</Button>
        </div>
      </div>

      {loading ? (
        <div className="shimmer" style={{ height: "12rem", borderRadius: "0.75rem" }} />
      ) : bracket.rounds.length === 0 ? (
        <div style={{ ...card, minWidth: 0, textAlign: "center", color: "rgba(255,255,255,0.45)" }}>
          No bracket yet — pick a round and click <strong style={{ color: "#fff" }}>Generate / seed</strong>.
        </div>
      ) : (
        <div style={{ display: "flex", gap: "2rem", overflowX: "auto", paddingBottom: "1rem" }}>
          {bracket.rounds.map((rnd) => (
            <div key={rnd.round_number} style={{ display: "flex", flexDirection: "column", gap: "1rem", justifyContent: "space-around" }}>
              <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                {rnd.round_number === bracket.rounds.length ? "Final" : `Round ${rnd.round_number}`}
              </p>
              {rnd.matches.map((m) => (
                <MatchCard key={m.id} m={m} onWin={recordWinner} onScore={recordScore} onSave={saveLogistics} />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MatchCard({ m, onWin, onScore, onSave }: {
  m: BracketMatch;
  onWin: (m: BracketMatch, winner: string | null) => void;
  onScore: (m: BracketMatch, sa: number, sb: number) => void;
  onSave: (m: BracketMatch, link: string, time: string) => void;
}) {
  const [link, setLink] = useState(m.match_link || "");
  const [time, setTime] = useState(m.scheduled_at ? m.scheduled_at.slice(0, 16) : "");
  const [sa, setSa] = useState(m.score_a != null ? String(m.score_a) : "");
  const [sb, setSb] = useState(m.score_b != null ? String(m.score_b) : "");
  const done = m.status === "completed";
  const ready = !!m.side_a.team_id && !!m.side_b.team_id;
  const scoreChip = (v: number | null) =>
    v != null ? (
      <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "rgba(255,255,255,0.85)", marginLeft: "0.4rem" }}>{v}</span>
    ) : null;
  const sideRow = (side: BracketSide, teamId: string | null, score: number | null) => (
    <button
      style={sideBtn(m.winner_team_id === teamId, done || !ready)}
      disabled={done || !ready || !teamId}
      onClick={() => onWin(m, teamId)}
      title={done || !ready ? "" : "Click to record this side as the winner"}
    >
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{side.name}</span>
      {scoreChip(score)}
      {m.winner_team_id === teamId && <span style={{ fontSize: "0.7rem", marginLeft: "0.3rem" }}>🏆</span>}
    </button>
  );
  return (
    <div style={card}>
      {sideRow(m.side_a, m.side_a.team_id, m.score_a)}
      {sideRow(m.side_b, m.side_b.team_id, m.score_b)}
      {!done && ready && (
        <>
          {/* Referee score entry: higher score wins and the tree advances. */}
          <div style={{ display: "flex", gap: "0.3rem", marginTop: "0.2rem", alignItems: "center" }}>
            <input value={sa} onChange={(e) => setSa(e.target.value)} placeholder="score A" type="number" style={{ ...inp, flex: "none", width: "5rem" }} />
            <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.75rem" }}>vs</span>
            <input value={sb} onChange={(e) => setSb(e.target.value)} placeholder="score B" type="number" style={{ ...inp, flex: "none", width: "5rem" }} />
            <button
              onClick={() => onScore(m, Number(sa || 0), Number(sb || 0))}
              disabled={sa === "" || sb === ""}
              style={{ ...inp, flex: 1, cursor: sa === "" || sb === "" ? "not-allowed" : "pointer", color: "#4ade80", fontWeight: 700, textAlign: "center" }}
            >
              Record score
            </button>
          </div>
          <p style={{ fontSize: "0.62rem", color: "rgba(255,255,255,0.3)", margin: "0.1rem 0 0" }}>
            Enter the refereed score (higher wins), or click a side above to set the winner directly.
          </p>
          <div style={{ display: "flex", gap: "0.3rem", marginTop: "0.2rem" }}>
            <input value={link} onChange={(e) => setLink(e.target.value)} placeholder="join link" style={inp} />
            <input type="datetime-local" value={time} onChange={(e) => setTime(e.target.value)} style={{ ...inp, flex: "none", width: "10rem" }} />
            <button onClick={() => onSave(m, link, time)} style={{ ...inp, flex: "none", cursor: "pointer", color: "#e8503a", fontWeight: 700 }}>Save</button>
          </div>
        </>
      )}
    </div>
  );
}
