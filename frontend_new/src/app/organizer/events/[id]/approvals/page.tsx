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
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ApprovalRequest, ApprovalStatus, ApprovalRequestType } from "@/types";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { Textarea } from "@/components/ui/Input";

const TYPE_LABEL: Record<ApprovalRequestType, string> = {
  team_formation: "Team Formation",
  judge_assignment: "Judge Assignment",
  email_batch: "Email Batch",
  leaderboard_publish: "Leaderboard Publish",
  stage_transition: "Stage Transition",
  progression: "Round Progression",
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
  const [submittingReview, setSubmittingReview] = useState(false);

  const fetchAll = useCallback(async () => {
    if (!id) return;
    try {
      const [p, h] = await Promise.all([
        listPendingApprovals(id).catch(() => []),
        listApprovalHistory(id).catch(() => []),
      ]);
      setPending(p);
      setHistory(h);
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

  const openReview = (req: ApprovalRequest, action: "approved" | "rejected") => {
    setReviewTarget(req);
    setReviewAction(action);
    setReviewNotes("");
  };

  const handleSubmitReview = async () => {
    if (!reviewTarget || !reviewAction || !id) return;
    setSubmittingReview(true);
    try {
      await reviewApproval(id, reviewTarget.id, {
        action: reviewAction,
        review_notes: reviewNotes || undefined,
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
                  <PayloadPreview payload={req.payload} />
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
