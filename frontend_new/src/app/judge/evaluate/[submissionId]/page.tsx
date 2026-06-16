"use client";

export const dynamic = "force-dynamic";

import { Suspense, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Star, CheckCircle, ExternalLink, FileText, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { getEvaluations, submitEvaluation, getMe, getSubmission, listRoundRubric, getAssessmentGuide } from "@/lib/api";
import type { Evaluation, RubricCriterion, AssessmentGuide } from "@/types";
import Button from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import Navbar from "@/components/layout/Navbar";
import QuizGradeCard from "@/components/quiz/QuizGradeCard";

export default function EvaluatePage() {
  return (
    <Suspense fallback={null}>
      <EvaluateContent />
    </Suspense>
  );
}

function EvaluateContent() {
  const { submissionId } = useParams<{ submissionId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const teamName = searchParams.get("team") ?? "";
  const roundName = searchParams.get("round") ?? "";
  const attachmentsParam = searchParams.get("attachments") ?? "";
  const fallbackAttachments = attachmentsParam ? attachmentsParam.split(",").filter(Boolean) : [];

  const [attachmentUrls, setAttachmentUrls] = useState<string[]>(fallbackAttachments);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [myJudgeId, setMyJudgeId] = useState<string | null>(null);
  const [criteria, setCriteria] = useState<RubricCriterion[]>([]);
  const [critScores, setCritScores] = useState<Record<string, number>>({});
  const [guide, setGuide] = useState<AssessmentGuide | null>(null);
  const [guideOpen, setGuideOpen] = useState(true);
  const [quizContext, setQuizContext] = useState<{ roundId: string; teamId: string } | null>(null);

  // Total = sum of per-criterion scores. Max = sum of criteria max_score.
  const totalScore = criteria.reduce((sum, c) => sum + (critScores[c.id] ?? 0), 0);
  const maxTotal = criteria.reduce((sum, c) => sum + c.max_score, 0);

  useEffect(() => {
    if (!submissionId) return;
    (async () => {
      try {
        const [evals, me, submission] = await Promise.all([
          getEvaluations(submissionId).catch(() => []),
          getMe(),
          getSubmission(submissionId).catch(() => null),
        ]);
        setEvaluations(evals);
        setMyJudgeId(me.id);
        // Always load the submission's attachments from the backend so the
        // judge sees the project links/PDFs regardless of how they navigated
        // here (the query param is only a fallback).
        if (submission?.attachments?.length) {
          setAttachmentUrls(submission.attachments);
        }

        // Load the round's rubric criteria.
        let crit: RubricCriterion[] = [];
        if (submission?.round_id) {
          crit = await listRoundRubric(submission.round_id).catch(() => []);
          setCriteria(crit);
        }

        // Quiz context: if this round has a question paper for the team, the
        // QuizGradeCard surfaces the answer key + AI auto-grade (renders nothing
        // for non-quiz rounds).
        if (submission?.round_id && submission?.team_id) {
          setQuizContext({ roundId: submission.round_id, teamId: submission.team_id });
        }

        // Load the AI-assisted assessment guide for this submission's challenge.
        getAssessmentGuide(submissionId).then(setGuide).catch(() => setGuide(null));

        const mine = evals.find((e) => e.judge_id === me.id);
        if (mine) {
          setSubmitted(true);
          setFeedback(mine.feedback || "");
          // Pre-fill per-criterion scores from the saved rubric breakdown.
          const saved = (mine.rubric_scores ?? {}) as Record<string, number>;
          const init: Record<string, number> = {};
          for (const c of crit) init[c.id] = Number(saved[c.id] ?? 0);
          setCritScores(init);
        }
      } catch {
        toast.error("Failed to load evaluation data");
      } finally {
        setLoading(false);
      }
    })();
  }, [submissionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!myJudgeId) {
      toast.error("Could not determine judge identity");
      return;
    }
    if (criteria.length === 0) {
      toast.error("No rubric criteria are configured for this round yet");
      return;
    }
    setSubmitting(true);
    try {
      // rubric_scores keyed by criterion id; the backend recomputes the total
      // as the sum (clamped to each criterion's max).
      const rubric: Record<string, number> = {};
      for (const c of criteria) rubric[c.id] = critScores[c.id] ?? 0;

      await submitEvaluation({
        submission_id: submissionId,
        judge_id: myJudgeId,
        total_score: totalScore,
        rubric_scores: rubric,
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

          {/* Project materials */}
          {!loading && (
            <div
              style={{
                borderRadius: "0.75rem",
                border: "1px solid #222",
                background: "#111",
                padding: "1.25rem",
              }}
            >
              <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.75rem" }}>
                Project Materials
              </p>
              {attachmentUrls.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {attachmentUrls.map((url, i) => {
                    const isPdf = url.toLowerCase().includes(".pdf") || url.includes("/submissions/files/");
                    return (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.875rem", color: "#6366f1", textDecoration: "none" }}
                      >
                        {isPdf ? <FileText size={14} /> : <ExternalLink size={14} />}
                        {isPdf ? `PDF document ${i + 1}` : (url.length > 60 ? url.slice(0, 60) + "…" : url)}
                      </a>
                    );
                  })}
                </div>
              ) : (
                <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>
                  No project materials were attached to this submission.
                </p>
              )}
            </div>
          )}

          {/* Quiz paper + answer key (quiz rounds only) */}
          {!loading && quizContext && (
            <QuizGradeCard
              roundId={quizContext.roundId}
              teamId={quizContext.teamId}
              submissionId={submissionId}
            />
          )}

          {/* Assessment guide */}
          {!loading && guide && (
            <div
              style={{
                borderRadius: "0.75rem",
                border: "1px solid rgba(232,80,58,0.25)",
                background: "linear-gradient(135deg, rgba(232,80,58,0.06), rgba(99,102,241,0.04))",
                padding: "1.25rem",
              }}
            >
              <button
                onClick={() => setGuideOpen((o) => !o)}
                style={{ display: "flex", alignItems: "center", gap: "0.5rem", width: "100%", background: "transparent", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}
              >
                <Sparkles size={16} color="#e8503a" />
                <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "#fff", flex: 1 }}>
                  Assessment Guide{guide.challenge ? ` · ${guide.challenge}` : ""}
                </span>
                <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.4)" }}>{guideOpen ? "Hide" : "Show"}</span>
              </button>

              {guideOpen && (
                <div style={{ marginTop: "0.85rem", display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                  {guide.overview && (
                    <p style={{ margin: 0, fontSize: "0.85rem", color: "rgba(255,255,255,0.7)", lineHeight: 1.5 }}>
                      {guide.overview}
                    </p>
                  )}

                  {guide.criteria_guides?.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                      {guide.criteria_guides.map((cg, i) => (
                        <div key={i} style={{ borderRadius: "0.5rem", border: "1px solid #1e1e1e", background: "rgba(255,255,255,0.02)", padding: "0.65rem 0.8rem" }}>
                          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "0.5rem" }}>
                            <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#fff" }}>{cg.criterion}</span>
                            {cg.max_score != null && (
                              <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.4)" }}>max {cg.max_score}</span>
                            )}
                          </div>
                          <p style={{ margin: "0.3rem 0 0", fontSize: "0.78rem", color: "rgba(255,255,255,0.65)", lineHeight: 1.45 }}>
                            {cg.what_to_look_for}
                          </p>
                          {cg.scoring_tips && (
                            <p style={{ margin: "0.3rem 0 0", fontSize: "0.74rem", color: "rgba(99,102,241,0.85)", lineHeight: 1.4 }}>
                              {cg.scoring_tips}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {guide.key_questions?.length > 0 && (
                    <div>
                      <p style={{ margin: "0 0 0.35rem", fontSize: "0.72rem", fontWeight: 600, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                        Key questions
                      </p>
                      <ul style={{ margin: 0, paddingLeft: "1.1rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        {guide.key_questions.map((q, i) => (
                          <li key={i} style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.4 }}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <span style={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.3)" }}>
                    {guide.generated_by === "ai" ? "AI-generated guidance — use your own judgment." : "Guidance derived from the round rubric."}
                  </span>
                </div>
              )}
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
                <p style={{ fontWeight: 700, color: "#4ade80", margin: 0, flex: 1 }}>
                  Evaluation Submitted
                </p>
                <button
                  onClick={() => setSubmitted(false)}
                  style={{
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    color: "#e8503a",
                    background: "transparent",
                    border: "1px solid rgba(232,80,58,0.3)",
                    borderRadius: "0.5rem",
                    padding: "0.35rem 0.75rem",
                    cursor: "pointer",
                  }}
                >
                  Edit score
                </button>
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
                    {totalScore}
                    <span
                      style={{
                        fontSize: "1.125rem",
                        color: "rgba(255,255,255,0.4)",
                      }}
                    >
                      /{maxTotal}
                    </span>
                  </p>
                </div>
              </div>
              {criteria.length > 0 && (
                <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                  {criteria.map((c) => (
                    <div key={c.id} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>
                      <span>{c.name}</span>
                      <span style={{ color: "#fff", fontWeight: 600 }}>{critScores[c.id] ?? 0}/{c.max_score}</span>
                    </div>
                  ))}
                </div>
              )}
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
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <label style={{ fontSize: "0.875rem", fontWeight: 600, color: "rgba(255,255,255,0.7)" }}>
                    Rubric Scoring
                  </label>
                  <span style={{ fontSize: "1.1rem", fontWeight: 900, color: "#e8503a" }}>
                    {totalScore}<span style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.4)" }}>/{maxTotal}</span>
                  </span>
                </div>

                {criteria.length === 0 ? (
                  <p style={{ fontSize: "0.85rem", color: "rgba(250,204,21,0.8)", margin: 0 }}>
                    No rubric has been set for this round yet. Ask the organizer to configure the rubric.
                  </p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    {criteria.map((c) => {
                      const val = critScores[c.id] ?? 0;
                      return (
                        <div key={c.id} style={{ borderRadius: "0.5rem", border: "1px solid #1e1e1e", background: "rgba(255,255,255,0.02)", padding: "0.75rem 0.875rem" }}>
                          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "0.5rem" }}>
                            <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff" }}>{c.name}</span>
                            <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)" }}>max {c.max_score}</span>
                          </div>
                          {c.description && (
                            <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: "0.2rem 0 0.5rem" }}>{c.description}</p>
                          )}
                          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                            <input
                              type="range"
                              min={0}
                              max={c.max_score}
                              step={1}
                              value={val}
                              onChange={(e) => setCritScores((p) => ({ ...p, [c.id]: Number(e.target.value) }))}
                              style={{ flex: 1, accentColor: "#e8503a", cursor: "pointer" }}
                            />
                            <input
                              type="number"
                              min={0}
                              max={c.max_score}
                              value={val}
                              onChange={(e) => {
                                const n = Math.max(0, Math.min(c.max_score, Number(e.target.value) || 0));
                                setCritScores((p) => ({ ...p, [c.id]: n }));
                              }}
                              style={{ width: "3.5rem", textAlign: "center", borderRadius: "0.4rem", border: "1px solid #222", background: "#0d0d0d", color: "#fff", padding: "0.3rem", fontSize: "0.85rem" }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
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
