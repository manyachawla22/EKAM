"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { updateApproval, getLeaderboard } from "@/lib/api";
import type { ApprovalRequest, Team, Judge, Participant, Submission } from "@/types";
import Button from "@/components/ui/Button";

interface Props {
  eventId: string;
  approval: ApprovalRequest;
  teams: Team[];
  judges: Judge[];
  participants: Participant[];
  onSaved: () => void;
}

const inputBase: React.CSSProperties = {
  borderRadius: "0.4rem",
  border: "1px solid #222",
  background: "#0d0d0d",
  padding: "0.35rem 0.5rem",
  fontSize: "0.8rem",
  color: "#fff",
  outline: "none",
};

const rowBox: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  padding: "0.4rem 0.6rem",
  borderRadius: "0.4rem",
  background: "rgba(255,255,255,0.03)",
  border: "1px solid #1e1e1e",
};

export default function ApprovalEditor({ eventId, approval, teams, judges, participants, onSaved }: Props) {
  const [payload, setPayload] = useState<Record<string, unknown>>(approval.payload || {});
  const [saving, setSaving] = useState(false);
  const [board, setBoard] = useState<Submission[]>([]);

  // Reset the editor only when a DIFFERENT approval is opened — NOT on every
  // background refetch of the same approval. Live SSE updates change the parent's
  // approval object reference frequently; depending on `approval` here would wipe
  // the organizer's in-progress edits (e.g. team moves) mid-edit (#8).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setPayload(approval.payload || {}), [approval.id]);

  const teamName = useMemo(() => {
    const m = new Map(teams.map((t) => [t.id, t.name]));
    return (id: string) => m.get(id) || `Team ${id.slice(0, 8)}`;
  }, [teams]);
  const judgeName = useMemo(() => {
    const m = new Map(judges.map((j) => [j.id, j.name]));
    return (id: string) => m.get(id) || `Judge ${id.slice(0, 8)}`;
  }, [judges]);
  const participantName = useMemo(() => {
    const m = new Map(participants.map((p) => [p.id, p.name]));
    return (id: string) => m.get(id) || id.slice(0, 8);
  }, [participants]);

  const type = approval.request_type as string;
  const currentStep = (payload.current_step as string) || "";
  const isAdvancement = type === "stage_transition" && currentStep.endsWith(":advancement");
  const roundId = payload.round_id as string | undefined;

  // Load the round leaderboard for advancement editing.
  useEffect(() => {
    if (isAdvancement && roundId) {
      getLeaderboard(roundId).then(setBoard).catch(() => setBoard([]));
    }
  }, [isAdvancement, roundId]);

  const save = async (next: Record<string, unknown>) => {
    setSaving(true);
    try {
      await updateApproval(eventId, approval.id, next);
      toast.success("Proposal updated");
      onSaved();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  // ── team_formation ──
  if (type === "team_formation") {
    const teamsObj = (payload.teams as Record<string, Array<{ id: string; name?: string; institution?: string }>>) || {};
    const rationales = (payload.rationales as Record<string, { rationale?: string; strengths?: string[]; watch_out_for?: string }>) || {};
    const keys = Object.keys(teamsObj);
    const moveMember = (memberId: string, fromKey: string, toKey: string) => {
      if (fromKey === toKey) return;
      const next = { ...teamsObj };
      next[fromKey] = (next[fromKey] || []).filter((m) => m.id !== memberId);
      const member = (teamsObj[fromKey] || []).find((m) => m.id === memberId);
      if (member) next[toKey] = [...(next[toKey] || []), member];
      setPayload((p) => ({ ...p, teams: next }));
    };
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "0.6rem" }}>
        {keys.map((k) => (
          <div key={k} style={{ ...rowBox, flexDirection: "column", alignItems: "stretch", gap: "0.4rem" }}>
            <strong style={{ fontSize: "0.8rem", color: "#fff" }}>Team {Number(k) + 1}</strong>
            {(teamsObj[k] || []).map((m) => (
              <div key={m.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ flex: 1, fontSize: "0.8rem", color: "rgba(255,255,255,0.75)" }}>
                  {m.name || participantName(m.id)}
                  {m.institution && (
                    <span style={{ color: "rgba(255,255,255,0.4)" }}> · {m.institution}</span>
                  )}
                </span>
                <select value={k} onChange={(e) => moveMember(m.id, k, e.target.value)} style={inputBase}>
                  {keys.map((kk) => <option key={kk} value={kk}>Team {Number(kk) + 1}</option>)}
                </select>
              </div>
            ))}
            {(teamsObj[k] || []).length === 0 && (
              <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)" }}>No members</span>
            )}
            {rationales[k]?.rationale && (
              <div style={{ marginTop: "0.3rem", paddingTop: "0.4rem", borderTop: "1px solid #1e1e1e", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                <p style={{ margin: 0, fontSize: "0.75rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.4 }}>
                  {rationales[k].rationale}
                </p>
                {(rationales[k].strengths || []).length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                    {(rationales[k].strengths || []).map((s, i) => (
                      <span key={i} style={{ fontSize: "0.68rem", color: "#4ade80", background: "rgba(74,222,128,0.1)", borderRadius: "0.3rem", padding: "0.1rem 0.4rem" }}>{s}</span>
                    ))}
                  </div>
                )}
                {rationales[k].watch_out_for && (
                  <p style={{ margin: 0, fontSize: "0.7rem", color: "rgba(250,204,21,0.8)" }}>
                    ⚠ {rationales[k].watch_out_for}
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
        <SaveBar saving={saving} onSave={() => save(payload)} />
      </div>
    );
  }

  // ── judge_assignment ──
  if (type === "judge_assignment") {
    const assignments = (payload.assignments as Array<{ judge_id: string; team_id: string }>) || [];
    const update = (next: Array<{ judge_id: string; team_id: string }>) =>
      setPayload((p) => ({ ...p, assignments: next }));
    const judgeLabel = (j: Judge) => (j.institution ? `${j.name} — ${j.institution}` : j.name);
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.6rem" }}>
        {assignments.map((a, i) => (
          <div key={i} style={rowBox}>
            <select value={a.judge_id} onChange={(e) => update(assignments.map((x, idx) => idx === i ? { ...x, judge_id: e.target.value } : x))} style={{ ...inputBase, flex: 1 }}>
              {judges.map((j) => <option key={j.id} value={j.id}>{judgeLabel(j)}</option>)}
            </select>
            <span style={{ color: "rgba(255,255,255,0.3)" }}>→</span>
            <select value={a.team_id} onChange={(e) => update(assignments.map((x, idx) => idx === i ? { ...x, team_id: e.target.value } : x))} style={{ ...inputBase, flex: 1 }}>
              {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <button onClick={() => update(assignments.filter((_, idx) => idx !== i))} style={{ background: "transparent", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: "0.75rem" }}>Remove</button>
          </div>
        ))}
        <button
          onClick={() => update([...assignments, { judge_id: judges[0]?.id || "", team_id: teams[0]?.id || "" }])}
          style={{ alignSelf: "flex-start", fontSize: "0.75rem", color: "#e8503a", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
        >
          + Add assignment
        </button>
        <SaveBar saving={saving} onSave={() => save(payload)} />
      </div>
    );
  }

  // ── stage_transition: advancement (editable) ──
  if (isAdvancement) {
    const cutoff = Number(payload.cutoff_score ?? 50);
    const override = payload.advancing_team_ids as string[] | undefined;
    const advancingSet = new Set(
      override ?? board.filter((s) => (s.final_score ?? 0) >= cutoff).map((s) => s.team_id)
    );
    const toggle = (teamId: string) => {
      const next = new Set(advancingSet);
      if (next.has(teamId)) next.delete(teamId);
      else next.add(teamId);
      setPayload((p) => ({ ...p, advancing_team_ids: Array.from(next) }));
    };
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.6rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.6)" }}>Cutoff</label>
          <input
            type="number" min={0} max={100} value={cutoff}
            onChange={(e) => setPayload((p) => ({ ...p, cutoff_score: Number(e.target.value), advancing_team_ids: undefined }))}
            style={{ ...inputBase, width: "5rem" }}
          />
          <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.35)" }}>or tick teams manually</span>
        </div>
        {board.map((s) => (
          <label key={s.id} style={{ ...rowBox, cursor: "pointer" }}>
            <input type="checkbox" checked={advancingSet.has(s.team_id)} onChange={() => toggle(s.team_id)} />
            <span style={{ flex: 1, fontSize: "0.8rem", color: "#fff" }}>{teamName(s.team_id)}</span>
            <span style={{ fontSize: "0.8rem", color: "#e8503a", fontWeight: 600 }}>{s.final_score ?? "—"}</span>
          </label>
        ))}
        {board.length === 0 && <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)" }}>No evaluated teams for this round.</span>}
        <SaveBar saving={saving} onSave={() => save(payload)} />
      </div>
    );
  }

  // ── stage_transition: winner announcement (review winners before sending) ──
  if (type === "stage_transition" && currentStep === "winner_announcement") {
    const winners = (payload.winners as Array<{ rank?: number; team_id: string; team_name?: string; score?: number }>) || [];
    const medals: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.6rem" }}>
        <p style={{ margin: 0, fontSize: "0.8rem", color: "rgba(255,255,255,0.7)" }}>
          Approving will <strong style={{ color: "#fff" }}>announce these winners</strong> and email each
          member their winner certificate. This can&apos;t be undone.
        </p>
        {winners.length > 0 ? (
          winners
            .slice()
            .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99))
            .map((w) => (
              <div key={w.team_id} style={rowBox}>
                <span style={{ fontSize: "1rem" }}>{medals[w.rank ?? 0] || `#${w.rank ?? "—"}`}</span>
                <span style={{ flex: 1, fontSize: "0.8rem", color: "#fff" }}>{w.team_name || teamName(w.team_id)}</span>
                <span style={{ fontSize: "0.8rem", color: "#e8503a", fontWeight: 600 }}>
                  {w.score != null ? Number(w.score).toFixed(1) : "—"}
                </span>
              </div>
            ))
        ) : (
          <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)" }}>No winners proposed.</span>
        )}
      </div>
    );
  }

  // ── stage_transition / progression: non-advancement (named summary) ──
  if (type === "stage_transition" || type === "progression") {
    const nextStep = (payload.next_step as string) || (payload.target_stage as string) || "";
    const advancing = (payload.advancing_teams as Array<{ team_name?: string; team_id: string }>) || [];
    return (
      <div style={{ marginTop: "0.6rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.7)" }}>
        <p style={{ margin: 0 }}>
          Advance pipeline{currentStep ? ` from "${prettyStep(currentStep)}"` : ""} → <strong style={{ color: "#fff" }}>{prettyStep(nextStep)}</strong>
        </p>
        {advancing.length > 0 && (
          <p style={{ margin: "0.4rem 0 0", color: "rgba(255,255,255,0.5)" }}>
            Advancing: {advancing.map((t) => t.team_name || teamName(t.team_id)).join(", ")}
          </p>
        )}
      </div>
    );
  }

  // ── email_batch ──
  if (type === "email_batch") {
    const subject = (payload.subject as string) || "";
    const bodyText = (payload.body_text as string) || "";
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.6rem" }}>
        <div>
          <label style={{ display: "block", fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", marginBottom: "0.2rem" }}>Subject</label>
          <input value={subject} onChange={(e) => setPayload((p) => ({ ...p, subject: e.target.value }))} style={{ ...inputBase, width: "100%" }} />
        </div>
        <div>
          <label style={{ display: "block", fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", marginBottom: "0.2rem" }}>Body (optional override)</label>
          <textarea value={bodyText} onChange={(e) => setPayload((p) => ({ ...p, body_text: e.target.value }))} rows={5} style={{ ...inputBase, width: "100%", resize: "vertical" }} />
        </div>
        <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.35)" }}>
          {(payload.recipient_count as number) ?? "?"} recipient(s)
        </span>
        <SaveBar saving={saving} onSave={() => save(payload)} />
      </div>
    );
  }

  // ── fallback: raw JSON editor ──
  return <JsonEditor value={payload} saving={saving} onSave={(v) => save(v)} />;
}

function prettyStep(step: string): string {
  if (!step) return "—";
  if (step.startsWith("round:")) {
    const phase = step.split(":")[2] || "";
    return `Round ${phase}`;
  }
  return step.replace(/_/g, " ");
}

function SaveBar({ saving, onSave }: { saving: boolean; onSave: () => void }) {
  return (
    <div style={{ marginTop: "0.4rem" }}>
      <Button variant="secondary" loading={saving} onClick={onSave}>Save edits</Button>
    </div>
  );
}

function JsonEditor({ value, saving, onSave }: { value: Record<string, unknown>; saving: boolean; onSave: (v: Record<string, unknown>) => void }) {
  const [text, setText] = useState(JSON.stringify(value, null, 2));
  useEffect(() => setText(JSON.stringify(value, null, 2)), [value]);
  return (
    <div style={{ marginTop: "0.6rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={10}
        style={{ ...inputBase, width: "100%", fontFamily: "monospace", fontSize: "0.72rem", resize: "vertical" }}
      />
      <div>
        <Button
          variant="secondary"
          loading={saving}
          onClick={() => {
            try {
              onSave(JSON.parse(text));
            } catch {
              toast.error("Invalid JSON");
            }
          }}
        >
          Save edits
        </Button>
      </div>
    </div>
  );
}
