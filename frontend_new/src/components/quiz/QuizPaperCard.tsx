"use client";

import { useEffect, useState } from "react";
import { FileQuestion } from "lucide-react";
import { getMyQuizPaper, type QuizPaper } from "@/lib/api";

/**
 * Participant view of THEIR question paper for a quiz round (feature #8). Shows the
 * questions (no answer key); the participant answers them in a single file and
 * uploads it via the normal submission flow below. Renders nothing if the selected
 * round isn't a quiz round / has no paper.
 */
export default function QuizPaperCard({ roundId }: { roundId: string }) {
  const [paper, setPaper] = useState<QuizPaper | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!roundId) { setPaper(null); return; }
    getMyQuizPaper(roundId)
      .then((p) => { if (!cancelled) setPaper(p); })
      .catch(() => { if (!cancelled) setPaper(null); });
    return () => { cancelled = true; };
  }, [roundId]);

  if (!paper || !paper.questions.length) return null;

  return (
    <div style={{ borderRadius: "0.6rem", border: "1px solid rgba(99,102,241,0.25)", background: "rgba(99,102,241,0.06)", padding: "0.9rem 1rem" }}>
      <p style={{ display: "flex", alignItems: "center", gap: "0.4rem", margin: "0 0 0.5rem", fontSize: "0.85rem", fontWeight: 700, color: "#c7d2fe" }}>
        <FileQuestion size={15} /> Your Question Paper
        {paper.total_marks ? <span style={{ marginLeft: "auto", fontWeight: 500, color: "rgba(255,255,255,0.5)", fontSize: "0.75rem" }}>{paper.total_marks} marks</span> : null}
      </p>
      <p style={{ margin: "0 0 0.6rem", fontSize: "0.72rem", color: "rgba(255,255,255,0.45)" }}>
        Answer all questions in a single file and upload it below.
      </p>
      <ol style={{ margin: 0, paddingLeft: "1.1rem", display: "flex", flexDirection: "column", gap: "0.55rem" }}>
        {paper.questions.map((q) => (
          <li key={q.id} style={{ fontSize: "0.82rem", color: "#fff" }}>
            {q.text} <span style={{ color: "rgba(255,255,255,0.35)" }}>({q.marks}m)</span>
            {q.options.length > 0 && (
              <div style={{ marginTop: "0.25rem", fontSize: "0.78rem", color: "rgba(255,255,255,0.6)", display: "flex", flexDirection: "column", gap: "0.1rem" }}>
                {q.options.map((o, oi) => (
                  <span key={oi}>{String.fromCharCode(97 + oi)}) {o}</span>
                ))}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
