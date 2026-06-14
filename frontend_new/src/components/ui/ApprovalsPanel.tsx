"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, XCircle, ChevronDown, Bell } from "lucide-react";
import { toast } from "sonner";
import {
  listPendingApprovals,
  reviewApproval,
  autoFormTeams,
} from "@/lib/api";
import { useEventStream } from "@/lib/useEventStream";
import type { ApprovalRequest, ApprovalRequestType } from "@/types";

const LABEL: Record<ApprovalRequestType, string> = {
  team_formation: "Team Formation",
  judge_assignment: "Judge Assignment",
  email_batch: "Email Batch",
  leaderboard_publish: "Leaderboard Publication",
  stage_transition: "Stage Transition",
  progression: "Progression",
  registration_form: "Registration Form",
  event_deploy: "Event Deployment",
  anomaly_review: "Scoring Anomaly",
};

const DESCRIPTION: Record<ApprovalRequestType, string> = {
  team_formation: "CP-SAT has proposed balanced teams. Review and approve to create them.",
  judge_assignment: "CP-SAT has proposed judge assignments. Review and approve to confirm.",
  email_batch: "An email batch is ready to send. Approve to dispatch.",
  leaderboard_publish: "Leaderboard is ready to publish.",
  stage_transition: "A stage transition has been proposed.",
  progression: "A progression proposal is pending review.",
  registration_form: "A public registration form is ready. Approve to publish it.",
  event_deploy: "An AI-designed event is ready. Approve to publish the event and its registration form.",
  anomaly_review: "A scoring anomaly was flagged. Approve to ask the judge to review it, or reject to dismiss.",
};

interface Props {
  eventId: string;
}

export default function ApprovalsPanel({ eventId }: Props) {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [open, setOpen] = useState(false);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectNotes, setRejectNotes] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchApprovals = useCallback(async () => {
    try {
      const data = await listPendingApprovals(eventId);
      setApprovals(data.filter((a) => a.status === "pending"));
    } catch {
      // silent — don't interrupt the user with poll errors
    }
  }, [eventId]);

  // Live updates arrive via SSE (useEventStream below); this poll is a slow
  // safety net for dropped streams / non-JWT sessions.
  useEffect(() => {
    fetchApprovals();
    intervalRef.current = setInterval(fetchApprovals, 60_000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchApprovals]);

  // Live push: a new/approved/rejected approval or a pipeline advance means the
  // pending list likely changed — refetch immediately.
  useEventStream(["approval", "pipeline"], fetchApprovals);

  const handleApprove = async (approval: ApprovalRequest) => {
    setActionLoading(approval.id);
    try {
      await reviewApproval(eventId, approval.id, { action: "approved" });
      toast.success(`${LABEL[approval.request_type]} approved!`);
      await fetchApprovals();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRejectSubmit = async (approval: ApprovalRequest) => {
    if (!rejectNotes.trim()) {
      toast.error("Please describe the issue before rejecting.");
      return;
    }
    setActionLoading(approval.id);
    try {
      await reviewApproval(eventId, approval.id, {
        action: "rejected",
        review_notes: rejectNotes,
      });
      toast.success("Rejected. Re-running with your feedback…");
      setRejectingId(null);
      setRejectNotes("");
      await fetchApprovals();

      // Auto re-trigger team formation
      if (approval.request_type === "team_formation") {
        const res = await autoFormTeams(eventId, 4);
        toast.success(res.message || "New team formation proposal created.");
      }

      // Give the backend a moment to commit the new approval, then refresh
      setTimeout(fetchApprovals, 1500);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading(null);
    }
  };

  const pending = approvals.length;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "1.5rem",
        right: "1.5rem",
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        gap: "0.75rem",
      }}
    >
      {/* Expanded panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ duration: 0.18 }}
            style={{
              width: "min(24rem, calc(100vw - 3rem))",
              borderRadius: "1rem",
              border: "1px solid #2a2a2a",
              background: "#111",
              boxShadow: "0 20px 60px rgba(0,0,0,0.6)",
              overflow: "hidden",
            }}
          >
            {/* Panel header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "1rem 1.25rem",
                borderBottom: "1px solid #1e1e1e",
              }}
            >
              <span style={{ fontWeight: 700, fontSize: "0.875rem", color: "#fff" }}>
                Pending Approvals
                {pending > 0 && (
                  <span
                    style={{
                      marginLeft: "0.5rem",
                      background: "#e8503a",
                      color: "#fff",
                      borderRadius: "9999px",
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      padding: "0.1rem 0.45rem",
                    }}
                  >
                    {pending}
                  </span>
                )}
              </span>
              <button
                onClick={() => setOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "rgba(255,255,255,0.4)",
                  cursor: "pointer",
                  display: "flex",
                }}
              >
                <ChevronDown size={18} />
              </button>
            </div>

            {/* Approvals list */}
            <div style={{ maxHeight: "60vh", overflowY: "auto" }}>
              {pending === 0 ? (
                <div
                  style={{
                    padding: "2.5rem 1.25rem",
                    textAlign: "center",
                    color: "rgba(255,255,255,0.3)",
                    fontSize: "0.875rem",
                  }}
                >
                  No pending approvals
                </div>
              ) : (
                approvals.map((approval) => (
                  <div
                    key={approval.id}
                    style={{
                      padding: "1rem 1.25rem",
                      borderBottom: "1px solid #1a1a1a",
                    }}
                  >
                    <p style={{ fontWeight: 600, color: "#fff", margin: "0 0 0.25rem", fontSize: "0.875rem" }}>
                      {LABEL[approval.request_type]}
                    </p>
                    <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", margin: "0 0 0.875rem", lineHeight: 1.5 }}>
                      {DESCRIPTION[approval.request_type]}
                    </p>

                    {rejectingId === approval.id ? (
                      /* Rejection form */
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        <textarea
                          value={rejectNotes}
                          onChange={(e) => setRejectNotes(e.target.value)}
                          placeholder="Describe the issue or constraints you want applied…"
                          rows={3}
                          style={{
                            width: "100%",
                            borderRadius: "0.5rem",
                            border: "1px solid #333",
                            background: "#0d0d0d",
                            color: "#fff",
                            fontSize: "0.8rem",
                            padding: "0.5rem 0.75rem",
                            resize: "vertical",
                            outline: "none",
                            fontFamily: "inherit",
                            boxSizing: "border-box",
                          }}
                        />
                        <div style={{ display: "flex", gap: "0.5rem" }}>
                          <button
                            onClick={() => { setRejectingId(null); setRejectNotes(""); }}
                            style={{
                              flex: 1,
                              padding: "0.4rem",
                              borderRadius: "0.4rem",
                              border: "1px solid #333",
                              background: "transparent",
                              color: "rgba(255,255,255,0.5)",
                              fontSize: "0.75rem",
                              cursor: "pointer",
                            }}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleRejectSubmit(approval)}
                            disabled={actionLoading === approval.id}
                            style={{
                              flex: 1,
                              padding: "0.4rem",
                              borderRadius: "0.4rem",
                              border: "none",
                              background: "#e8503a",
                              color: "#fff",
                              fontSize: "0.75rem",
                              fontWeight: 600,
                              cursor: actionLoading === approval.id ? "not-allowed" : "pointer",
                              opacity: actionLoading === approval.id ? 0.6 : 1,
                            }}
                          >
                            {actionLoading === approval.id ? "Sending…" : "Reject & Re-run"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* Approve / Reject buttons */
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button
                          onClick={() => { setRejectingId(approval.id); setRejectNotes(""); }}
                          style={{
                            flex: 1,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "0.35rem",
                            padding: "0.45rem",
                            borderRadius: "0.4rem",
                            border: "1px solid rgba(239,68,68,0.35)",
                            background: "rgba(239,68,68,0.08)",
                            color: "#f87171",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          <XCircle size={14} /> Reject
                        </button>
                        <button
                          onClick={() => handleApprove(approval)}
                          disabled={actionLoading === approval.id}
                          style={{
                            flex: 1,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "0.35rem",
                            padding: "0.45rem",
                            borderRadius: "0.4rem",
                            border: "none",
                            background: "#22c55e",
                            color: "#fff",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            cursor: actionLoading === approval.id ? "not-allowed" : "pointer",
                            opacity: actionLoading === approval.id ? 0.6 : 1,
                          }}
                        >
                          <CheckCircle size={14} />
                          {actionLoading === approval.id ? "…" : "Approve"}
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB toggle button */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.97 }}
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          padding: "0.75rem 1.125rem",
          borderRadius: "9999px",
          border: "none",
          background: pending > 0 ? "#e8503a" : "#1a1a1a",
          color: pending > 0 ? "#fff" : "rgba(255,255,255,0.6)",
          fontWeight: 700,
          fontSize: "0.875rem",
          cursor: "pointer",
          boxShadow: pending > 0
            ? "0 4px 20px rgba(232,80,58,0.45)"
            : "0 4px 16px rgba(0,0,0,0.4)",
          transition: "background 0.2s, box-shadow 0.2s",
          fontFamily: "inherit",
        }}
      >
        <Bell size={16} />
        Approvals
        {pending > 0 && (
          <span
            style={{
              background: "#fff",
              color: "#e8503a",
              borderRadius: "9999px",
              fontSize: "0.7rem",
              fontWeight: 800,
              padding: "0.1rem 0.45rem",
              lineHeight: 1.4,
            }}
          >
            {pending}
          </span>
        )}
      </motion.button>
    </div>
  );
}
