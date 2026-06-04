"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, Zap, UserCheck, Mail, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  listJudges,
  inviteJudge,
  deleteJudge,
  listRounds,
  autoAssignJudges,
  uploadJudgesCsv,
  getJudgeAssignments,
  getEvaluations,
} from "@/lib/api";
import type { JudgeAssignmentDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Judge, Round } from "@/types";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Modal from "@/components/ui/Modal";
import CsvUploadButton from "@/components/ui/CsvUploadButton";

const inputBase: React.CSSProperties = {
  width: "100%",
  borderRadius: "0.5rem",
  border: "1px solid #222",
  background: "#0d0d0d",
  padding: "0.625rem 0.75rem",
  fontSize: "0.875rem",
  color: "#fff",
  outline: "none",
  fontFamily: "inherit",
  boxSizing: "border-box",
};

export default function JudgesPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();

  const [judges, setJudges] = useState<Judge[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [autoAssigning, setAutoAssigning] = useState(false);
  const [selectedRound, setSelectedRound] = useState<string>("");

  const [inviteForm, setInviteForm] = useState({ email: "", name: "" });
  const [detailJudge, setDetailJudge] = useState<{ judge: Judge; assignments: JudgeAssignmentDetail[]; avgScore: number | null } | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user || !id) {
      setLoading(false);
      return;
    }
    Promise.all([
      listJudges(id).catch(() => []),
      listRounds(id).catch(() => []),
    ])
      .then(([j, r]) => {
        setJudges(j);
        setRounds(r);
        if (r.length > 0) setSelectedRound(r[0].id);
      })
      .catch((err: Error) => toast.error(err.message || "Failed to load data"))
      .finally(() => setLoading(false));
  }, [id, authLoading, user]);

  const handleDelete = async (judgeId: string) => {
    if (!id || !window.confirm("Remove this judge from the event?")) return;
    try {
      await deleteJudge(id, judgeId);
      setJudges((prev) => prev.filter((j) => j.id !== judgeId));
      toast.success("Judge removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove judge");
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteForm.email || !id) {
      toast.error("Email is required");
      return;
    }
    setInviting(true);
    try {
      await inviteJudge({
        email: inviteForm.email,
        event_id: id,
        name: inviteForm.name || undefined,
      });
      toast.success("Invitation sent!");
      setInviteModalOpen(false);
      setInviteForm({ email: "", name: "" });
      const updated = await listJudges(id);
      setJudges(updated);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to send invitation"
      );
    } finally {
      setInviting(false);
    }
  };

  const handleAutoAssign = async () => {
    if (!id) return;
    setAutoAssigning(true);
    try {
      const result = await autoAssignJudges(id, 3);
      toast.success(result.message || "Auto-assigned judges — review in Approvals.");
      const updated = await listJudges(id);
      setJudges(updated);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Auto-assign failed");
    } finally {
      setAutoAssigning(false);
    }
  };

  const openJudgeDetail = async (j: Judge) => {
    if (!id) return;
    setDetailLoading(true);
    setDetailJudge({ judge: j, assignments: [], avgScore: null });
    try {
      const assgns = await getJudgeAssignments(id, j.id).catch(() => [] as JudgeAssignmentDetail[]);
      const evalScores: number[] = [];
      for (const a of assgns.filter((a) => a.already_evaluated && a.submission_id)) {
        const evals = await getEvaluations(a.submission_id!).catch(() => []);
        const mine = evals.find((e) => e.judge_id === j.id);
        if (mine) evalScores.push(mine.total_score ?? mine.score ?? 0);
      }
      const avg = evalScores.length > 0 ? Math.round(evalScores.reduce((a, b) => a + b, 0) / evalScores.length) : null;
      setDetailJudge({ judge: j, assignments: assgns, avgScore: avg });
    } catch {
      // keep partial
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <div
        style={{
          marginBottom: "2rem",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#fff",
              margin: 0,
            }}
          >
            Judges
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            {judges.length} judge{judges.length !== 1 ? "s" : ""} assigned
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          <CsvUploadButton
            label="Bulk Import CSV"
            disabled={!id}
            onUpload={(file) => uploadJudgesCsv(id, file)}
            onUploaded={async () => {
              if (!id) return;
              try {
                setJudges(await listJudges(id));
              } catch (err) {
                toast.error(err instanceof Error ? err.message : "Imported, but failed to refresh the list — reload the page.");
              }
            }}
          />
          <Button variant="primary" onClick={() => setInviteModalOpen(true)}>
            <Plus size={16} /> Invite Judge
          </Button>
        </div>
      </div>

      {rounds.length > 0 && (
        <div
          style={{
            marginBottom: "2rem",
            borderRadius: "0.75rem",
            border: "1px solid rgba(232,80,58,0.2)",
            background: "rgba(232,80,58,0.05)",
            padding: "1.25rem",
          }}
        >
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "1rem",
            }}
          >
            <div>
              <h3
                style={{
                  fontWeight: 600,
                  color: "#fff",
                  margin: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <Zap size={16} color="#e8503a" />
                Auto-Assign Judges
              </h3>
              <p
                style={{
                  marginTop: "0.25rem",
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.5)",
                }}
              >
                Automatically distribute judges across all teams for a round.
              </p>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                flexWrap: "wrap",
              }}
            >
              <select
                value={selectedRound}
                onChange={(e) => setSelectedRound(e.target.value)}
                style={{ ...inputBase, width: "auto", padding: "0.5rem 0.75rem" }}
              >
                {rounds.map((r) => (
                  <option key={r.id} value={r.id} style={{ background: "#111" }}>
                    {r.name}
                  </option>
                ))}
              </select>
              <Button
                variant="primary"
                loading={autoAssigning}
                onClick={handleAutoAssign}
              >
                <Zap size={16} /> Auto-Assign
              </Button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "4rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : judges.length === 0 ? (
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
            <UserCheck size={32} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>
            No judges yet. Invite judges to this event.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {judges.map((j, i) => (
            <motion.div
              key={j.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "1rem",
                borderRadius: "0.75rem",
                border: "1px solid #222",
                background: "#111",
                padding: "1rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  height: "2.5rem",
                  width: "2.5rem",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "9999px",
                  background: "rgba(168,85,247,0.15)",
                  color: "#c084fc",
                  flexShrink: 0,
                }}
              >
                <UserCheck size={20} />
              </div>
              <button
                onClick={() => openJudgeDetail(j)}
                style={{ flex: 1, minWidth: 0, background: "transparent", border: "none", cursor: "pointer", textAlign: "left", padding: 0 }}
              >
                <p style={{ fontWeight: 500, color: "#fff", margin: 0, textDecoration: "underline", textDecorationColor: "rgba(255,255,255,0.15)", textUnderlineOffset: "2px" }}>
                  {j.name || j.email}
                </p>
                {j.email && (
                  <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>{j.email}</p>
                )}
              </button>
              {j.institution && (
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.4)",
                    background: "#222",
                    borderRadius: "9999px",
                    padding: "0.25rem 0.625rem",
                  }}
                >
                  {j.institution}
                </span>
              )}
              <button
                onClick={() => handleDelete(j.id)}
                title="Remove judge"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "rgba(255,255,255,0.2)",
                  padding: "0.25rem",
                  borderRadius: "0.375rem",
                  transition: "color 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#f87171")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(255,255,255,0.2)")}
              >
                <Trash2 size={15} />
              </button>
            </motion.div>
          ))}
        </div>
      )}

      {/* Judge detail modal */}
      <Modal open={!!detailJudge} onClose={() => setDetailJudge(null)} title={detailJudge ? `Judge: ${detailJudge.judge.name || detailJudge.judge.email}` : ""} size="lg">
        {detailJudge && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div style={{ padding: "1rem", borderRadius: "0.5rem", background: "#0d0d0d" }}>
              <p style={{ fontSize: "0.875rem", color: "#fff", fontWeight: 600, margin: "0 0 0.25rem" }}>{detailJudge.judge.email}</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.5)", marginTop: "0.5rem" }}>
                {detailJudge.judge.institution && <span>Institution: {detailJudge.judge.institution}</span>}
              </div>
              {(detailJudge.judge.expertise ?? []).length > 0 && (
                <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                  {(detailJudge.judge.expertise ?? []).map((e) => (
                    <span key={e} style={{ fontSize: "0.7rem", padding: "0.15rem 0.5rem", borderRadius: "9999px", background: "rgba(168,85,247,0.15)", color: "#c084fc" }}>{e}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Eval stats */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem" }}>
              {[
                { label: "Assigned", value: detailJudge.assignments.length },
                { label: "Completed", value: detailJudge.assignments.filter((a) => a.already_evaluated).length },
                { label: "Avg Score Given", value: detailJudge.avgScore !== null ? `${detailJudge.avgScore}` : "—" },
              ].map(({ label, value }) => (
                <div key={label} style={{ padding: "0.75rem", borderRadius: "0.5rem", background: "#0d0d0d", textAlign: "center" }}>
                  <p style={{ fontSize: "1.25rem", fontWeight: 700, color: "#e8503a", margin: 0 }}>{value}</p>
                  <p style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>{label}</p>
                </div>
              ))}
            </div>

            {/* Judge log */}
            <div>
              <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Judge Log</p>
              {detailLoading ? (
                <div className="shimmer" style={{ height: "4rem", borderRadius: "0.375rem" }} />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {detailJudge.judge.created_at && (
                    <div style={{ display: "flex", gap: "0.75rem" }}>
                      <div style={{ width: "8px", height: "8px", borderRadius: "9999px", background: "#e8503a", flexShrink: 0, marginTop: "0.3rem" }} />
                      <div>
                        <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", margin: 0 }}>Invited as judge</p>
                        <p style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>{new Date(detailJudge.judge.created_at).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}</p>
                      </div>
                    </div>
                  )}
                  {detailJudge.assignments
                    .filter((a) => a.already_evaluated)
                    .map((a) => (
                      <div key={a.assignment_id} style={{ display: "flex", gap: "0.75rem" }}>
                        <div style={{ width: "8px", height: "8px", borderRadius: "9999px", background: "#4ade80", flexShrink: 0, marginTop: "0.3rem" }} />
                        <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", margin: 0 }}>
                          Evaluated {a.team_name} — {a.round_name}
                        </p>
                      </div>
                    ))}
                  {detailJudge.assignments.length > 0 && (
                    <div style={{ display: "flex", gap: "0.75rem" }}>
                      <div style={{ width: "8px", height: "8px", borderRadius: "9999px", background: "#6366f1", flexShrink: 0, marginTop: "0.3rem" }} />
                      <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", margin: 0 }}>
                        Assigned to {detailJudge.assignments.length} team{detailJudge.assignments.length !== 1 ? "s" : ""}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      <Modal
        open={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        title="Invite Judge"
      >
        <form
          onSubmit={handleInvite}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <div
            style={{
              borderRadius: "0.5rem",
              background: "rgba(59,130,246,0.1)",
              border: "1px solid rgba(59,130,246,0.2)",
              padding: "0.75rem 1rem",
              fontSize: "0.875rem",
              color: "#60a5fa",
              display: "flex",
              alignItems: "flex-start",
              gap: "0.5rem",
            }}
          >
            <Mail size={16} style={{ marginTop: "0.125rem", flexShrink: 0 }} />
            An invitation email will be sent to the judge with access instructions.
          </div>
          <Input
            label="Email Address *"
            type="email"
            value={inviteForm.email}
            onChange={(e) =>
              setInviteForm((p) => ({ ...p, email: e.target.value }))
            }
            placeholder="judge@example.com"
            fullWidth
            required
          />
          <Input
            label="Name (optional)"
            value={inviteForm.name}
            onChange={(e) =>
              setInviteForm((p) => ({ ...p, name: e.target.value }))
            }
            placeholder="Judge's full name"
            fullWidth
          />
          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setInviteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={inviting}
              style={{ flex: 1 }}
            >
              Send Invitation
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
