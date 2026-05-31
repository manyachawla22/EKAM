"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Star, CheckCircle, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { getEvaluations, submitEvaluation, getMe } from "@/lib/api";
import type { Evaluation } from "@/types";
import Button from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import Navbar from "@/components/layout/Navbar";

export default function EvaluatePage() {
  const { submissionId } = useParams<{ submissionId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const teamName = searchParams.get("team") ?? "";
  const roundName = searchParams.get("round") ?? "";
  const attachmentsParam = searchParams.get("attachments") ?? "";
  const attachmentUrls = attachmentsParam ? attachmentsParam.split(",").filter(Boolean) : [];

  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [score, setScore] = useState(50);
  const [feedback, setFeedback] = useState("");
  const [myJudgeId, setMyJudgeId] = useState<string | null>(null);

  useEffect(() => {
    if (!submissionId) return;
    Promise.all([
      getEvaluations(submissionId).catch(() => []),
      getMe(),
    ])
      .then(([evals, me]) => {
        setEvaluations(evals);
        setMyJudgeId(me.id);
        const mine = evals.find((e) => e.judge_id === me.id);
        if (mine) {
          setSubmitted(true);
          // Backend returns `total_score`; older copies of the type still
          // expose `score`. Prefer total_score, fall back to score.
          setScore(mine.total_score ?? mine.score ?? 0);
          setFeedback(mine.feedback || "");
        }
      })
      .catch(() => toast.error("Failed to load evaluation data"))
      .finally(() => setLoading(false));
  }, [submissionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!myJudgeId) {
      toast.error("Could not determine judge identity");
      return;
    }
    if (score < 0 || score > 100) {
      toast.error("Score must be between 0 and 100");
      return;
    }
    setSubmitting(true);
    try {
      await submitEvaluation({
        submission_id: submissionId,
        judge_id: myJudgeId,
        total_score: score,
        // Until the backend exposes a per-round rubric schema, we send a
        // single-key rubric so the request validates and the score round-
        // trips intact in `rubric_scores`.
        rubric_scores: { overall: score },
        feedback: feedback || undefined,
      });
      setSubmitted(true);
      toast.success("Evaluation submitted!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const pageWrap: React.CSSProperties = {
    minHeight: "100vh",
    background: "#0a0a0a",
  };
  const container: React.CSSProperties = {
    maxWidth: "42rem",
    margin: "0 auto",
    padding: "6rem 1.5rem 3rem",
  };
  const card: React.CSSProperties = {
    borderRadius: "0.75rem",
    border: "1px solid #222",
    background: "#111",
    padding: "1.5rem",
  };

  return (
    <div style={pageWrap}>
      <Navbar />
      <div style={container}>
        <button
          onClick={() => router.back()}
          style={{
            marginBottom: "1.5rem",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.875rem",
            color: "rgba(255,255,255,0.4)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
        >
          <ArrowLeft size={16} />
          Back
        </button>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "1.5rem",
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
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <Star size={24} color="#e8503a" />
              {teamName ? `Evaluate: ${teamName}` : "Evaluate Submission"}
            </h1>
            <p
              style={{
                marginTop: "0.25rem",
                fontSize: "0.875rem",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              {roundName && <>{roundName} · </>}
              Submission #{String(submissionId).slice(0, 8)}
            </p>
          </div>

          {/* Project links */}
          {attachmentUrls.length > 0 && (
            <div
              style={{
                borderRadius: "0.75rem",
                border: "1px solid #222",
                background: "#111",
                padding: "1.25rem",
              }}
            >
              <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.75rem" }}>
                Project Links
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {attachmentUrls.map((url, i) => (
                  <a
                    key={i}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.875rem", color: "#6366f1", textDecoration: "none" }}
                  >
                    <ExternalLink size={14} />
                    {url.length > 60 ? url.slice(0, 60) + "…" : url}
                  </a>
                ))}
              </div>
            </div>
          )}

          {loading ? (
            <div
              className="shimmer"
              style={{ height: "15rem", borderRadius: "0.75rem" }}
            />
          ) : submitted ? (
            <div
              style={{
                borderRadius: "0.75rem",
                border: "1px solid rgba(34,197,94,0.2)",
                background: "rgba(34,197,94,0.1)",
                padding: "1.5rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  marginBottom: "1rem",
                }}
              >
                <CheckCircle size={24} color="#4ade80" />
                <p style={{ fontWeight: 700, color: "#4ade80", margin: 0 }}>
                  Evaluation Submitted
                </p>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                }}
              >
                <div>
                  <p
                    style={{
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.4)",
                      margin: 0,
                    }}
                  >
                    Your Score
                  </p>
                  <p
                    style={{
                      fontSize: "2rem",
                      fontWeight: 900,
                      color: "#fff",
                      margin: 0,
                    }}
                  >
                    {score}
                    <span
                      style={{
                        fontSize: "1.125rem",
                        color: "rgba(255,255,255,0.4)",
                      }}
                    >
                      /100
                    </span>
                  </p>
                </div>
              </div>
              {feedback && (
                <div
                  style={{
                    marginTop: "1rem",
                    borderRadius: "0.5rem",
                    background: "rgba(255,255,255,0.05)",
                    padding: "1rem",
                  }}
                >
                  <p
                    style={{
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.4)",
                      marginBottom: "0.25rem",
                    }}
                  >
                    Feedback
                  </p>
                  <p
                    style={{
                      fontSize: "0.875rem",
                      color: "rgba(255,255,255,0.7)",
                      margin: 0,
                    }}
                  >
                    {feedback}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <form
              onSubmit={handleSubmit}
              style={{
                ...card,
                display: "flex",
                flexDirection: "column",
                gap: "1.5rem",
              }}
            >
              <div>
                <label
                  style={{
                    marginBottom: "0.75rem",
                    display: "block",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    color: "rgba(255,255,255,0.7)",
                  }}
                >
                  Score (0–100)
                </label>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "1rem",
                  }}
                >
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={score}
                    onChange={(e) => setScore(parseInt(e.target.value))}
                    style={{
                      flex: 1,
                      height: "0.5rem",
                      accentColor: "#e8503a",
                      cursor: "pointer",
                    }}
                  />
                  <div
                    style={{
                      display: "flex",
                      height: "3.5rem",
                      width: "3.5rem",
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: "0.75rem",
                      border: "1px solid rgba(232,80,58,0.3)",
                      background: "rgba(232,80,58,0.1)",
                      fontSize: "1.25rem",
                      fontWeight: 900,
                      color: "#e8503a",
                      flexShrink: 0,
                    }}
                  >
                    {score}
                  </div>
                </div>
                <div
                  style={{
                    marginTop: "0.5rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.25rem",
                  }}
                >
                  {Array.from({ length: 10 }).map((_, i) => {
                    const threshold = (i + 1) * 10;
                    return (
                      <div
                        key={i}
                        style={{
                          flex: 1,
                          height: "0.375rem",
                          borderRadius: "9999px",
                          background:
                            score >= threshold ? "#e8503a" : "#222",
                          transition: "all 0.2s",
                        }}
                      />
                    );
                  })}
                </div>
              </div>

              <Textarea
                label="Feedback (optional)"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Provide constructive feedback for the team..."
                fullWidth
              />

              {evaluations.length > 0 && (
                <div>
                  <p
                    style={{
                      marginBottom: "0.75rem",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "rgba(255,255,255,0.3)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    Other Evaluations ({evaluations.length})
                  </p>
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.5rem",
                    }}
                  >
                    {evaluations.map((ev) => (
                      <div
                        key={ev.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.75rem",
                          borderRadius: "0.5rem",
                          background: "rgba(255,255,255,0.03)",
                          padding: "0.5rem 0.75rem",
                          fontSize: "0.875rem",
                        }}
                      >
                        <span
                          style={{ fontWeight: 700, color: "#e8503a" }}
                        >
                          {ev.total_score ?? ev.score}
                        </span>
                        <span style={{ color: "rgba(255,255,255,0.4)" }}>
                          by Judge #{String(ev.judge_id).slice(0, 8)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                fullWidth
                loading={submitting}
              >
                <Star size={16} />
                Submit Evaluation
              </Button>
            </form>
          )}
        </motion.div>
      </div>
    </div>
  );
}
