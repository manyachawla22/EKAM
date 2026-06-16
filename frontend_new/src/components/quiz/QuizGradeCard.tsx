"use client";

import { useEffect, useState } from "react";
import { FileQuestion, Sparkles, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import Button from "@/components/ui/Button";
import { getTeamQuizPaper, autoGradeQuiz, type QuizPaper } from "@/lib/api";

/**
 * Judge/organizer grading view of a team's question paper for a quiz round
 * (feature #8). Shows each question WITH the answer key so the judge can grade
 * per question, plus an "AI auto-grade" button that scores the uploaded answer
 * file against the key. Renders nothing if the round isn't a quiz round.
 */
export default function QuizGradeCard({
  roundId, teamId, submissionId, onGraded,
}: {
  roundId: string;
  teamId: string;
  submissionId: string;
  onGraded?: (total: number) => void;
}) {
  const [paper, setPaper] = useState<QuizPaper | null>(null);
  const [grading, setGrading] = useState(false);
  const [result, setResult] = useState<{ total?: number; results?: Array<{ number: number; correct: boolean; awarded: number }> } | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!roundId || !teamId) { setPaper(null); return; }
    getTeamQuizPaper(roundId, teamId)
      .then((p) => { if (!cancelled) setPaper(p); })
      .catch(() => { if (!cancelled) setPaper(null); });
    return () => { cancelled = true; };
  }, [roundId, teamId]);

  if (!paper || !paper.questions.length) return null;

  const hasAnswerKey = paper.questions.some((q) => q.correct_answer);
  const resultByNumber = new Map((result?.results ?? []).map((r) => [r.number, r]));

  const runAutoGrade = async () => {
    setGrading(true);
    try {
      const res = await autoGradeQuiz(submissionId);
      if (!res.graded) {
        toast.error(res.reason || "Could not auto-grade this submission.");
        return;
      }
      setResult({ total: res.total, results: res.results });
      toast.success(`AI scored ${res.total} marks.`);
      if (res.total != null) onGraded?.(res.total);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Auto-grade failed");
    } finally {
      setGrading(false);
    }
  };

  return (
    <div style={{ borderRadius: "0.75rem", border: "1px solid rgba(99,102,241,0.25)", background: "rgba(99,102,241,0.06)", padding: "1.25rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <FileQuestion size={16} color="#c7d2fe" />
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#c7d2fe", flex: 1 }}>
          Question Paper{paper.total_marks ? ` · ${paper.total_marks} marks` : ""}
        </span>
        {hasAnswerKey && (
          <Button variant="secondary" disabled={grading} loading={grading} onClick={runAutoGrade}>
            <Sparkles size={14} /> AI auto-grade
          </Button>
        )}
      </div>

      {result?.total != null && (
        <div style={{ marginBottom: "0.75rem", fontSize: "0.8rem", color: "#4ade80" }}>
          AI awarded <strong>{result.total}</strong> marks — review the per-question breakdown below, then set your rubric score.
        </div>
      )}

      <ol style={{ margin: 0, paddingLeft: "1.1rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        {paper.questions.map((q) => {
          const r = q.number != null ? resultByNumber.get(q.number) : undefined;
          return (
            <li key={q.id || q.number} style={{ fontSize: "0.82rem", color: "#fff" }}>
              <span>
                {q.text} <span style={{ color: "rgba(255,255,255,0.35)" }}>({q.marks}m)</span>
              </span>
              {q.options.length > 0 && (
                <div style={{ marginTop: "0.25rem", fontSize: "0.78rem", color: "rgba(255,255,255,0.6)", display: "flex", flexDirection: "column", gap: "0.1rem" }}>
                  {q.options.map((o, oi) => (
                    <span key={oi}>{String.fromCharCode(97 + oi)}) {o}</span>
                  ))}
                </div>
              )}
              {q.correct_answer && (
                <div style={{ marginTop: "0.2rem", fontSize: "0.75rem", color: "#4ade80" }}>
                  Answer: {q.correct_answer}
                </div>
              )}
              {r && (
                <div style={{ marginTop: "0.2rem", display: "inline-flex", alignItems: "center", gap: "0.3rem", fontSize: "0.74rem", color: r.correct ? "#4ade80" : "#f87171" }}>
                  {r.correct ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                  {r.correct ? "Correct" : "Incorrect"} · {r.awarded}m
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
