"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { FileUp, Wand2 } from "lucide-react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import {
  listQuizQuestions, uploadQuizBank, uploadQuizBankText,
  setQuizConfig, generateQuizPapers, type QuizBank,
} from "@/lib/api";

/**
 * Organizer question-bank manager for a quiz round (feature #8). Upload a .md/.csv
 * bank (or paste it), set how many questions per paper, generate per-team papers,
 * and review the bank. Opening it on a round turns that round into a quiz round.
 */
export default function QuizBankModal({
  open, roundId, roundName, onClose,
}: { open: boolean; roundId: string | null; roundName?: string; onClose: () => void }) {
  const [bank, setBank] = useState<QuizBank | null>(null);
  const [loading, setLoading] = useState(false);
  const [perPaper, setPerPaper] = useState(0);
  const [pasteText, setPasteText] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    if (!roundId) return;
    setLoading(true);
    try {
      const b = await listQuizQuestions(roundId);
      setBank(b);
      setPerPaper(b.questions_per_paper || b.bank_size || 0);
    } catch {
      setBank(null);
    } finally {
      setLoading(false);
    }
  }, [roundId]);

  useEffect(() => { if (open && roundId) refresh(); }, [open, roundId, refresh]);

  const onFile = async (file: File) => {
    if (!roundId) return;
    setBusy(true);
    try {
      const res = await uploadQuizBank(roundId, file);
      toast.success(res.message);
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const onPaste = async () => {
    if (!roundId || !pasteText.trim()) return;
    setBusy(true);
    try {
      const res = await uploadQuizBankText(roundId, pasteText, "bank.md");
      toast.success(res.message);
      setPasteText("");
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to import");
    } finally {
      setBusy(false);
    }
  };

  const saveConfig = async () => {
    if (!roundId) return;
    setBusy(true);
    try {
      await setQuizConfig(roundId, perPaper);
      toast.success("Saved.");
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setBusy(false);
    }
  };

  const generate = async () => {
    if (!roundId) return;
    setBusy(true);
    try {
      const res = await generateQuizPapers(roundId);
      const judges = res.judges_assigned
        ? ` · ${res.judges_assigned} judge assignment(s)`
        : "";
      toast.success(`Generated ${res.created} paper(s).${judges}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to generate");
    } finally {
      setBusy(false);
    }
  };

  const lbl: React.CSSProperties = { fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" };
  const numInp: React.CSSProperties = {
    width: "5rem", borderRadius: "0.4rem", border: "1px solid #222", background: "#0d0d0d",
    padding: "0.4rem 0.5rem", fontSize: "0.85rem", color: "#fff", outline: "none",
  };

  return (
    <Modal open={open} onClose={onClose} title={`Question Bank — ${roundName || "Round"}`} size="lg">
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {loading ? (
          <div className="shimmer" style={{ height: "4rem", borderRadius: "0.5rem" }} />
        ) : (
          <>
            <div style={{ display: "flex", gap: "1.5rem", fontSize: "0.85rem", color: "#fff", flexWrap: "wrap" }}>
              <span>Bank: <strong>{bank?.bank_size ?? 0}</strong> questions</span>
              <span>Per paper: <strong>{bank?.questions_per_paper ?? 0}</strong></span>
              <span>Quiz round: <strong>{bank?.is_quiz ? "yes" : "no"}</strong></span>
            </div>

            {/* Upload / paste */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", padding: "0.85rem", borderRadius: "0.6rem", border: "1px solid #222", background: "#0d0d0d" }}>
              <span style={lbl}>Import a bank — a .md/.txt or .csv file, or paste below.</span>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <Button variant="secondary" disabled={busy} onClick={() => fileRef.current?.click()}>
                  <FileUp size={14} /> Upload .md / .csv
                </Button>
                <input
                  ref={fileRef} type="file" accept=".md,.txt,.csv" style={{ display: "none" }}
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.currentTarget.value = ""; }}
                />
              </div>
              <textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder={"Paste questions here, e.g.\n1. What is 2+2?\na) 3\nb) 4\nAnswer: b\nMarks: 1"}
                rows={5}
                style={{ width: "100%", borderRadius: "0.4rem", border: "1px solid #222", background: "#111", padding: "0.5rem", fontSize: "0.8rem", color: "#fff", outline: "none", fontFamily: "monospace", boxSizing: "border-box" }}
              />
              <Button variant="secondary" disabled={busy || !pasteText.trim()} onClick={onPaste}>
                Import pasted questions
              </Button>
            </div>

            {/* Config + generate */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <span style={lbl}>Questions per paper</span>
              <input type="number" min={1} max={bank?.bank_size || 99} value={perPaper}
                onChange={(e) => setPerPaper(Number(e.target.value))} style={numInp} />
              <Button variant="secondary" disabled={busy} onClick={saveConfig}>Save</Button>
              <Button variant="primary" disabled={busy || !bank?.bank_size} onClick={generate}>
                <Wand2 size={14} /> Generate papers
              </Button>
            </div>

            {/* Bank preview */}
            {bank && bank.questions.length > 0 && (
              <div style={{ maxHeight: "16rem", overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {bank.questions.map((q, i) => (
                  <div key={q.id || i} style={{ padding: "0.6rem 0.75rem", borderRadius: "0.5rem", background: "#0d0d0d", border: "1px solid #1e1e1e" }}>
                    <p style={{ margin: 0, fontSize: "0.82rem", color: "#fff" }}>{i + 1}. {q.text} <span style={{ color: "rgba(255,255,255,0.35)" }}>({q.marks}m)</span></p>
                    {q.options.length > 0 && (
                      <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>
                        {q.options.map((o, oi) => `${String.fromCharCode(97 + oi)}) ${o}`).join("   ")}
                      </p>
                    )}
                    {q.correct_answer && (
                      <p style={{ margin: "0.2rem 0 0", fontSize: "0.72rem", color: "#4ade80" }}>Answer: {q.correct_answer}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
