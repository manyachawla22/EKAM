"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Send, ExternalLink } from "lucide-react";
import TeamDetailModal from "@/components/ui/TeamDetailModal";
import { toast } from "sonner";
import { listRounds, listSubmissions } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useAutoRefresh } from "@/lib/useAutoRefresh";
import type { Submission, Round } from "@/types";
import Badge from "@/components/ui/Badge";

const statusVariant: Record<string, "info" | "success" | "warning" | "danger" | "default"> = {
  pending: "warning",
  reviewed: "info",
  flagged: "danger",
  finalised: "success",
};

interface SubmissionWithRound extends Submission {
  roundName?: string;
}

export default function SubmissionsPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const [submissions, setSubmissions] = useState<SubmissionWithRound[]>([]);
  const [loading, setLoading] = useState(true);
  const [teamModal, setTeamModal] = useState<{ teamId: string; teamName: string } | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const rounds: Round[] = await listRounds(id).catch(() => []);
      // Fetch every round's submissions in parallel rather than sequentially.
      const perRound = await Promise.all(
        rounds.map(async (r) => {
          const subs = await listSubmissions(r.id).catch(() => []);
          return subs.map((s) => ({ ...s, roundName: r.name }));
        })
      );
      setSubmissions(perRound.flat());
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to load submissions"
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (authLoading) return;
    if (!user || !id) {
      setLoading(false);
      return;
    }
    load();
  }, [id, authLoading, user, load]);

  useAutoRefresh(() => {
    if (user && id) load();
  });

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1
          style={{
            fontSize: "1.5rem",
            fontWeight: 900,
            fontStyle: "italic",
            color: "#fff",
            margin: 0,
          }}
        >
          Submissions
        </h1>
        <p
          style={{
            marginTop: "0.25rem",
            fontSize: "0.875rem",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          {submissions.length} submission{submissions.length !== 1 ? "s" : ""}
        </p>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "4rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : submissions.length === 0 ? (
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
            <Send size={32} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>No submissions yet</p>
        </div>
      ) : (
        <div
          style={{
            borderRadius: "0.75rem",
            border: "1px solid #222",
            background: "#111",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.5fr 1fr 1fr 1fr 1.2fr",
              gap: "1rem",
              borderBottom: "1px solid #222",
              padding: "0.75rem 1.25rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "rgba(255,255,255,0.3)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>Team</span>
            <span>Round</span>
            <span>Status</span>
            <span>Score</span>
            <span>Submitted</span>
          </div>
          {submissions.map((s, i) => (
            <motion.div
              key={s.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
              style={{
                display: "grid",
                gridTemplateColumns: "1.5fr 1fr 1fr 1fr 1.2fr",
                gap: "1rem",
                alignItems: "center",
                borderBottom:
                  i === submissions.length - 1
                    ? "none"
                    : "1px solid rgba(34,34,34,0.5)",
                padding: "0.875rem 1.25rem",
              }}
            >
              <button
                onClick={() => setTeamModal({
                  teamId: s.team_id,
                  teamName: s.team?.name || `Team ${String(s.team_id).slice(0, 8)}`,
                })}
                style={{
                  background: "transparent", border: "none", cursor: "pointer",
                  padding: 0, textAlign: "left",
                  fontSize: "0.875rem", fontWeight: 500, color: "#fff",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  textDecoration: "underline", textDecorationColor: "rgba(255,255,255,0.15)",
                  textUnderlineOffset: "3px", transition: "color 0.15s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#e8503a")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#fff")}
              >
                {s.team?.name || `Team ${String(s.team_id).slice(0, 8)}`}
              </button>
              <span
                style={{
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.6)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {s.roundName || s.round?.name || "—"}
              </span>
              <span>
                <Badge variant={statusVariant[s.status] || "default"}>
                  {s.status}
                </Badge>
              </span>
              <span style={{ fontSize: "0.875rem", color: "#fff" }}>
                {s.final_score != null ? (
                  <span style={{ fontWeight: 600, color: "#e8503a" }}>
                    {s.final_score}
                  </span>
                ) : (
                  <span style={{ color: "rgba(255,255,255,0.3)" }}>—</span>
                )}
              </span>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.4)",
                  }}
                >
                  {s.submitted_at
                    ? new Date(s.submitted_at).toLocaleDateString()
                    : "—"}
                </span>
                <a
                  href={`/judge/evaluate/${s.id}`}
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 500,
                    color: "#e8503a",
                    whiteSpace: "nowrap",
                  }}
                >
                  Evaluate →
                </a>
                {s.attachments && s.attachments.length > 0 && (
                  <a
                    href={s.attachments[0]}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "#e8503a", display: "flex" }}
                  >
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {teamModal && id && (
        <TeamDetailModal
          open={!!teamModal}
          onClose={() => setTeamModal(null)}
          eventId={id}
          teamId={teamModal.teamId}
          teamName={teamModal.teamName}
        />
      )}
    </div>
  );
}
