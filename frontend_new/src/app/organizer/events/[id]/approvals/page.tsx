"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Check,
  X,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import {
  listPendingApprovals,
  listApprovalHistory,
  reviewApproval,
  listTeams,
  listJudges,
  listParticipants,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useAutoRefresh } from "@/lib/useAutoRefresh";
import type { ApprovalRequest, ApprovalStatus, ApprovalRequestType, Team, Judge, Participant } from "@/types";
import Button from "@/components/ui/Button";
import ApprovalEditor from "@/components/approvals/ApprovalEditor";
import Modal from "@/components/ui/Modal";
import { Textarea } from "@/components/ui/Input";

const TYPE_LABEL: Record<ApprovalRequestType, string> = {
  team_formation: "Team Formation",
  judge_assignment: "Judge Assignment",
  email_batch: "Email Batch",
  leaderboard_publish: "Leaderboard Publish",
  stage_transition: "Stage Transition",
  progression: "Round Progression",
  registration_form: "Registration Form",
  event_deploy: "Event Deployment",
};

const STATUS_STYLE: Record<
  ApprovalStatus,
  { background: string; color: string; border: string; label: string }
> = {
  draft: {
    background: "rgba(148,163,184,0.12)",
    color: "#94a3b8",
    border: "rgba(148,163,184,0.25)",
    label: "Draft",
  },
  pending: {
    background: "rgba(234,179,8,0.12)",
    color: "#fbbf24",
    border: "rgba(234,179,8,0.3)",
    label: "Pending",
  },
  approved: {
    background: "rgba(34,197,94,0.12)",
    color: "#4ade80",
    border: "rgba(34,197,94,0.3)",
    label: "Approved",
  },
  rejected: {
    background: "rgba(239,68,68,0.12)",
    color: "#f87171",
    border: "rgba(239,68,68,0.3)",
    label: "Rejected",
  },
  revised: {
    background: "rgba(99,102,241,0.12)",
    color: "#a5b4fc",
    border: "rgba(99,102,241,0.3)",
    label: "Revised",
  },
};

function StatusBadge({ status }: { status: ApprovalStatus }) {
  const s = STATUS_STYLE[status];
  return (
    <span
      style={{
        fontSize: "0.7rem",
        fontWeight: 600,
        padding: "0.2rem 0.55rem",
        borderRadius: "9999px",
        background: s.background,
        color: s.color,
        border: `1px solid ${s.border}`,
        textTransform: "uppercase",
        letterSpacing: "0.02em",
      }}
    >
      {s.label}
    </span>
  );
}

function PayloadPreview({ payload }: { payload: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  // Produce a couple of quick summary chips for common payload shapes.
  const summary: string[] = [];
  const teams = (payload as { teams?: unknown[] }).teams;
  if (Array.isArray(teams)) summary.push(`${teams.length} teams`);
  const assignments = (payload as { assignments?: unknown[] }).assignments;
  if (Array.isArray(assignments)) summary.push(`${assignments.length} assignments`);
  const leftovers = (payload as { leftovers?: unknown[] }).leftovers;
  if (Array.isArray(leftovers) && leftovers.length)
    summary.push(`${leftovers.length} leftover`);
  if (!summary.length) summary.push(`${Object.keys(payload).length} fields`);

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.4rem",
          background: "transparent",
          border: "none",
          color: "#e8503a",
          fontSize: "0.75rem",
          fontWeight: 500,
          cursor: "pointer",
          padding: 0,
        }}
      >
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {summary.join(" · ")} — {open ? "hide" : "view"} proposal
      </button>
      <AnimatePresence>
        {open && (
          <motion.pre
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            style={{
              marginTop: "0.6rem",
              maxHeight: "20rem",
              overflow: "auto",
              borderRadius: "0.5rem",
              background: "#0a0a0a",
              border: "1px solid #222",
              padding: "0.75rem",
              fontSize: "0.7rem",
              color: "rgba(255,255,255,0.7)",
              lineHeight: 1.55,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {JSON.stringify(payload, null, 2)}
          </motion.pre>
        )}
      </AnimatePresence>
    </div>
  );
}

function prettyStepLabel(step: string): string {
  if (!step) return "—";
  if (step.startsWith("round:")) {
    const phase = step.split(":")[2] || "";
    return `Round ${phase}`;
  }
  return step.replace(/_/g, " ");
}

// Read-only, human-readable rendering of a resolved approval's payload, so the
// History tab shows real names (teams, judges, participants) instead of raw JSON.
function ApprovalSummary({
  approval,
  teams,
  judges,
  participants,
}: {
  approval: ApprovalRequest;
  teams: Team[];
  judges: Judge[];
  participants: Participant[];
}) {
  const teamName = (idVal: string) =>
    teams.find((t) => t.id === idVal)?.name || `Team ${idVal.slice(0, 8)}`;
  const judgeName = (idVal: string) =>
    judges.find((j) => j.id === idVal)?.name || `Judge ${idVal.slice(0, 8)}`;
  const participantName = (idVal: string) =>
    participants.find((p) => p.id === idVal)?.name || idVal.slice(0, 8);

  const payload = (approval.payload || {}) as Record<string, unknown>;
  const type = approval.request_type as string;
  const line: React.CSSProperties = { fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", margin: "0.15rem 0" };

  if (type === "team_formation") {
    const teamsObj = (payload.teams as Record<string, Array<{ id: string; name?: string; institution?: string }>>) || {};
    const keys = Object.keys(teamsObj);
    return (
      <div>
        {keys.map((k) => (
          <p key={k} style={line}>
            <strong style={{ color: "#fff" }}>Team {Number(k) + 1}:</strong>{" "}
            {(teamsObj[k] || [])
              .map((m) => {
                const nm = m.name || participantName(m.id);
                return m.institution ? `${nm} (${m.institution})` : nm;
              })
              .join(", ") || "—"}
          </p>
        ))}
      </div>
    );
  }

  if (type === "judge_assignment") {
    const assignments = (payload.assignments as Array<{ judge_id: string; team_id: string; judge_name?: string; judge_institution?: string; team_name?: string }>) || [];
    return (
      <div>
        {assignments.map((a, i) => {
          const jn = a.judge_name || judgeName(a.judge_id);
          const jLabel = a.judge_institution ? `${jn} — ${a.judge_institution}` : jn;
          const tn = a.team_name || teamName(a.team_id);
          return (
            <p key={i} style={line}>
              {jLabel} → <strong style={{ color: "#fff" }}>{tn}</strong>
            </p>
          );
        })}
      </div>
    );
  }

  if (type === "stage_transition" || type === "progression") {
    const currentStep = (payload.current_step as string) || "";
    const nextStep = (payload.next_step as string) || (payload.target_stage as string) || "";
    const advancing = (payload.advancing_teams as Array<{ team_name?: string; team_id: string }>) || [];
    const eliminated = (payload.eliminated_teams as Array<{ team_name?: string; team_id: string }>) || [];
    const cutoff = payload.cutoff_score;
    return (
      <div>
        <p style={line}>
          Advance pipeline{currentStep ? ` from "${prettyStepLabel(currentStep)}"` : ""} →{" "}
          <strong style={{ color: "#fff" }}>{prettyStepLabel(nextStep)}</strong>
        </p>
        {cutoff != null && <p style={line}>Cutoff score: {String(cutoff)}</p>}
        {advancing.length > 0 && (
          <p style={line}>Advancing: {advancing.map((t) => t.team_name || teamName(t.team_id)).join(", ")}</p>
        )}
        {eliminated.length > 0 && (
          <p style={line}>Eliminated: {eliminated.map((t) => t.team_name || teamName(t.team_id)).join(", ")}</p>
        )}
      </div>
    );
  }

  if (type === "email_batch") {
    return (
      <div>
        <p style={line}>
          <strong style={{ color: "#fff" }}>{(payload.subject as string) || "(no subject)"}</strong>
        </p>
        <p style={line}>{(payload.recipient_count as number) ?? "?"} recipient(s)</p>
      </div>
    );
  }

  return <PayloadPreview payload={approval.payload} />;
}

export default function ApprovalsPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const [pending, setPending] = useState<ApprovalRequest[]>([]);
  const [history, setHistory] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"pending" | "history">("pending");

  const [reviewTarget, setReviewTarget] = useState<ApprovalRequest | null>(null);
  const [reviewAction, setReviewAction] = useState<"approved" | "rejected" | null>(
    null
  );
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewCutoff, setReviewCutoff] = useState(50);
  const [submittingReview, setSubmittingReview] = useState(false);

  // Lookup data so proposals can show real names (and editors offer choices).
  const [teamsList, setTeamsList] = useState<Team[]>([]);
  const [judgesList, setJudgesList] = useState<Judge[]>([]);
  const [participantsList, setParticipantsList] = useState<Participant[]>([]);

  const fetchAll = useCallback(async () => {
    if (!id) return;
    try {
      const [p, h, t, j, pa] = await Promise.all([
        listPendingApprovals(id).catch(() => []),
        listApprovalHistory(id).catch(() => []),
        listTeams(id).catch(() => [] as Team[]),
        listJudges(id).catch(() => [] as Judge[]),
        listParticipants(id).catch(() => [] as Participant[]),
      ]);
      setPending(p);
      setHistory(h);
      setTeamsList(t);
      setJudgesList(j);
      setParticipantsList(pa);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    fetchAll();
  }, [authLoading, user, fetchAll]);

  useAutoRefresh(() => {
    if (user && id) fetchAll();
  });

  const openReview = (req: ApprovalRequest, action: "approved" | "rejected") => {
    setReviewTarget(req);
    setReviewAction(action);
    setReviewNotes("");
  };

  const isAdvancementReview = (req: ApprovalRequest | null): boolean => {
    const step = (req?.payload as { current_step?: string } | undefined)?.current_step;
    return typeof step === "string" && step.endsWith(":advancement");
  };

  const handleSubmitReview = async () => {
    if (!reviewTarget || !reviewAction || !id) return;
    setSubmittingReview(true);
    try {
      await reviewApproval(id, reviewTarget.id, {
        action: reviewAction,
        review_notes: reviewNotes || undefined,
        cutoff_score:
          reviewAction === "approved" && isAdvancementReview(reviewTarget)
            ? reviewCutoff
            : undefined,
      });
      toast.success(
        reviewAction === "approved" ? "Approved" : "Rejected"
      );
      setReviewTarget(null);
      setReviewAction(null);
      await fetchAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Review failed");
    } finally {
      setSubmittingReview(false);
    }
  };

  const tabs: Array<{
    key: "pending" | "history";
    label: string;
    count: number;
  }> = [
    { key: "pending", label: "Pending", count: pending.length },
    { key: "history", label: "History", count: history.length },
  ];
  const current = tab === "pending" ? pending : history;

  const card: React.CSSProperties = {
    borderRadius: "0.75rem",
    border: "1px solid #222",
    background: "#111",
    padding: "1.25rem",
  };

  return (
    <div style={{ maxWidth: "60rem", margin: "0 auto", width: "100%" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1
          style={{
            fontSize: "1.5rem",
            fontWeight: 900,
            fontStyle: "italic",
            color: "#fff",
            margin: 0,
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
          }}
        >
          <ShieldCheck size={22} color="#e8503a" />
          Approvals
        </h1>
        <p
          style={{
            marginTop: "0.25rem",
            fontSize: "0.875rem",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          Review proposed team formations, judge assignments, and other
          automated actions before they commit.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          gap: "0.4rem",
          marginBottom: "1.5rem",
          borderBottom: "1px solid #222",
          paddingBottom: "0.4rem",
        }}
      >
        {tabs.map((t) => {
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                background: active ? "rgba(232,80,58,0.1)" : "transparent",
                color: active ? "#e8503a" : "rgba(255,255,255,0.6)",
                border: "1px solid",
                borderColor: active ? "rgba(232,80,58,0.25)" : "transparent",
                padding: "0.4rem 0.85rem",
                borderRadius: "0.5rem",
                fontSize: "0.85rem",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              {t.label}{" "}
              <span
                style={{
                  fontSize: "0.7rem",
                  color: active ? "#e8503a" : "rgba(255,255,255,0.35)",
                  marginLeft: "0.25rem",
                }}
              >
                ({t.count})
              </span>
            </button>
          );
        })}
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "7rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : current.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.75rem",
            padding: "4rem 0",
            textAlign: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              height: "3.5rem",
              width: "3.5rem",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "1rem",
              background: "#111",
              border: "1px solid #222",
            }}
          >
            <ShieldCheck size={26} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)", margin: 0 }}>
            {tab === "pending"
              ? "Nothing waiting on you right now."
              : "No reviewed approvals yet."}
          </p>
          {tab === "pending" && (
            <p
              style={{
                fontSize: "0.8rem",
                color: "rgba(255,255,255,0.3)",
                maxWidth: "24rem",
                margin: 0,
              }}
            >
              Approvals appear here when you trigger auto-form-teams,
              auto-assign-judges, or other batch actions.
            </p>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {current.map((req, i) => {
            const isActionable = req.status === "pending";
            return (
              <motion.div
                key={req.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                style={card}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: "0.75rem",
                    flexWrap: "wrap",
                  }}
                >
                  <div>
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
                          margin: 0,
                          fontSize: "1rem",
                          fontWeight: 600,
                          color: "#fff",
                        }}
                      >
                        {TYPE_LABEL[req.request_type] || req.request_type}
                      </h3>
                      <StatusBadge status={req.status} />
                    </div>
                    <p
                      style={{
                        margin: "0.35rem 0 0",
                        fontSize: "0.75rem",
                        color: "rgba(255,255,255,0.4)",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.35rem",
                      }}
                    >
                      <Clock size={11} />
                      Requested{" "}
                      {new Date(req.requested_at).toLocaleString()}
                      {req.reviewed_at && (
                        <span>
                          {" · "}reviewed{" "}
                          {new Date(req.reviewed_at).toLocaleString()}
                        </span>
                      )}
                    </p>
                    {req.review_notes && (
                      <p
                        style={{
                          marginTop: "0.5rem",
                          padding: "0.5rem 0.7rem",
                          background: "rgba(255,255,255,0.03)",
                          borderRadius: "0.4rem",
                          fontSize: "0.75rem",
                          color: "rgba(255,255,255,0.6)",
                          fontStyle: "italic",
                        }}
                      >
                        Note: {req.review_notes}
                      </p>
                    )}
                  </div>
                  {isActionable && (
                    <div
                      style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}
                    >
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => openReview(req, "rejected")}
                      >
                        <X size={14} /> Reject
                      </Button>
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => openReview(req, "approved")}
                      >
                        <Check size={14} /> Approve
                      </Button>
                    </div>
                  )}
                </div>

                <div style={{ marginTop: "0.85rem" }}>
                  {isActionable ? (
                    <ApprovalEditor
                      eventId={id}
                      approval={req}
                      teams={teamsList}
                      judges={judgesList}
                      participants={participantsList}
                      onSaved={fetchAll}
                    />
                  ) : (
                    <PayloadPreview payload={req.payload} />
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      <Modal
        open={!!reviewTarget && !!reviewAction}
        onClose={() => {
          setReviewTarget(null);
          setReviewAction(null);
        }}
        title={
          reviewAction === "approved"
            ? "Approve this request?"
            : "Reject this request?"
        }
      >
        <div
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <div
            style={{
              borderRadius: "0.5rem",
              background:
                reviewAction === "approved"
                  ? "rgba(34,197,94,0.08)"
                  : "rgba(239,68,68,0.08)",
              border:
                reviewAction === "approved"
                  ? "1px solid rgba(34,197,94,0.2)"
                  : "1px solid rgba(239,68,68,0.2)",
              padding: "0.75rem 1rem",
              fontSize: "0.85rem",
              color: "rgba(255,255,255,0.75)",
              display: "flex",
              alignItems: "flex-start",
              gap: "0.5rem",
            }}
          >
            <AlertTriangle size={16} style={{ marginTop: "0.15rem", flexShrink: 0 }} />
            {reviewAction === "approved"
              ? "Approving will execute the proposed action immediately (e.g. commit team formations, send invitations)."
              : "Rejecting cancels the proposal. The requester will need to re-trigger if they want to retry."}
          </div>
          {reviewAction === "approved" && isAdvancementReview(reviewTarget) && (
            <div>
              <label style={{ display: "block", marginBottom: "0.375rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>
                Qualifying cutoff score
              </label>
              <input
                type="number"
                min={0}
                max={100}
                value={reviewCutoff}
                onChange={(e) => setReviewCutoff(Number(e.target.value))}
                style={{ width: "100%", borderRadius: "0.5rem", border: "1px solid #222", background: "#0d0d0d", padding: "0.5rem 0.75rem", fontSize: "0.875rem", color: "#fff", outline: "none" }}
              />
              <p style={{ marginTop: "0.3rem", fontSize: "0.72rem", color: "rgba(255,255,255,0.4)" }}>
                Teams scoring at or above this advance; the rest receive a failure email and are blocked from later rounds.
              </p>
            </div>
          )}
          <Textarea
            label="Notes (optional)"
            placeholder="Reason / comments for the requester…"
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            fullWidth
          />
          <div
            style={{ display: "flex", gap: "0.6rem", paddingTop: "0.25rem" }}
          >
            <Button
              variant="secondary"
              onClick={() => {
                setReviewTarget(null);
                setReviewAction(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant={reviewAction === "approved" ? "primary" : "danger"}
              loading={submittingReview}
              style={{ flex: 1 }}
              onClick={handleSubmitReview}
            >
              {reviewAction === "approved" ? (
                <>
                  <Check size={14} /> Confirm Approval
                </>
              ) : (
                <>
                  <X size={14} /> Confirm Rejection
                </>
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
