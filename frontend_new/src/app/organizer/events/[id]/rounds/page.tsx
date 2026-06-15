"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, Layers, Calendar, SlidersHorizontal, CalendarClock, FileQuestion } from "lucide-react";
import { toast } from "sonner";
import { listRounds, createRound, updateRoundWindow } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Round, RoundStatus } from "@/types";
import Button from "@/components/ui/Button";
import Input, { Select } from "@/components/ui/Input";
import { RoundStatusBadge } from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";
import RubricEditorModal from "@/components/rubric/RubricEditorModal";
import QuizBankModal from "@/components/quiz/QuizBankModal";

/** Small per-round feature pill (Quiz / Live / Blind) derived from the round flags. */
function RoundFlagBadge({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      padding: "0.1rem 0.5rem", borderRadius: "9999px", fontSize: "0.65rem", fontWeight: 700,
      background: `${color}1f`, color, border: `1px solid ${color}55`, letterSpacing: "0.02em",
    }}>
      {label}
    </span>
  );
}

export default function RoundsPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();

  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [rubricRound, setRubricRound] = useState<Round | null>(null);
  const [quizRound, setQuizRound] = useState<Round | null>(null);

  const [form, setForm] = useState({
    name: "",
    status: "upcoming" as RoundStatus,
    start_date: "",
    end_date: "",
  });

  // Deadline-editing modal state.
  const [editRound, setEditRound] = useState<Round | null>(null);
  const [editForm, setEditForm] = useState({ start_date: "", end_date: "", reopen: false });
  const [savingWindow, setSavingWindow] = useState(false);

  // UTC ISO → value for a <input type="datetime-local"> (local wall-clock).
  const toLocalInput = (iso?: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  // datetime-local (local) → UTC ISO string, or null when cleared.
  const fromLocalInput = (v: string) => (v ? new Date(v).toISOString() : null);

  const openEdit = (round: Round) => {
    setEditRound(round);
    setEditForm({
      start_date: toLocalInput(round.start_date),
      end_date: toLocalInput(round.end_date),
      reopen: false,
    });
  };

  const handleSaveWindow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editRound || !id) return;
    setSavingWindow(true);
    try {
      const updated = await updateRoundWindow(id, editRound.id, {
        start_date: fromLocalInput(editForm.start_date),
        end_date: fromLocalInput(editForm.end_date),
        reopen: editForm.reopen,
      });
      setRounds((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setEditRound(null);
      toast.success(
        editForm.reopen ? "Deadline updated — affected teams reopened." : "Deadline updated."
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update deadline");
    } finally {
      setSavingWindow(false);
    }
  };

  const fetchRounds = useCallback(() => {
    if (!id) return;
    listRounds(id)
      .then(setRounds)
      .catch((err: Error) =>
        toast.error(err.message || "Failed to load rounds")
      )
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    fetchRounds();
  }, [authLoading, user, fetchRounds]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !id) {
      toast.error("Round name is required");
      return;
    }
    setCreating(true);
    try {
      const round = await createRound({
        event_id: id,
        name: form.name,
        status: form.status,
        start_date: form.start_date || undefined,
        end_date: form.end_date || undefined,
      });
      setRounds((prev) => [...prev, round]);
      setModalOpen(false);
      setForm({ name: "", status: "upcoming", start_date: "", end_date: "" });
      toast.success("Round created!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create round");
    } finally {
      setCreating(false);
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
            Rounds
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            Manage event rounds and their schedules
          </p>
        </div>
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          <Plus size={16} /> Add Round
        </Button>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "5rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : rounds.length === 0 ? (
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
            <Layers size={32} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>
            No rounds yet. Add the first round.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {rounds.map((round, i) => (
            <motion.div
              key={round.id}
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
                padding: "1.25rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  height: "2.5rem",
                  width: "2.5rem",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "0.5rem",
                  background: "rgba(232,80,58,0.1)",
                  color: "#e8503a",
                  fontWeight: 700,
                  fontSize: "0.875rem",
                  flexShrink: 0,
                }}
              >
                R{i + 1}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    flexWrap: "wrap",
                  }}
                >
                  <h3 style={{ fontWeight: 600, color: "#fff", margin: 0 }}>
                    {round.name}
                  </h3>
                  <RoundStatusBadge status={round.status} />
                  {round.is_quiz && <RoundFlagBadge label="Quiz" color="#6366f1" />}
                  {round.live_judging && <RoundFlagBadge label="Live" color="#4ade80" />}
                  {round.anonymous && <RoundFlagBadge label="Blind" color="#fbbf24" />}
                </div>
                {(round.start_date || round.end_date) && (
                  <div
                    style={{
                      marginTop: "0.25rem",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.5rem",
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.4)",
                      flexWrap: "wrap",
                    }}
                  >
                    <Calendar size={12} />
                    {round.start_date && (
                      <span>
                        Start: {new Date(round.start_date).toLocaleDateString()}
                      </span>
                    )}
                    {round.end_date && (
                      <span>
                        End: {new Date(round.end_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                )}
              </div>
              <Button variant="secondary" onClick={() => openEdit(round)}>
                <CalendarClock size={14} /> Deadline
              </Button>
              <Button variant="secondary" onClick={() => setRubricRound(round)}>
                <SlidersHorizontal size={14} /> Rubric
              </Button>
              <Button variant="secondary" onClick={() => setQuizRound(round)}>
                <FileQuestion size={14} /> Quiz
              </Button>
            </motion.div>
          ))}
        </div>
      )}

      <RubricEditorModal
        open={!!rubricRound}
        roundId={rubricRound?.id ?? null}
        roundName={rubricRound?.name}
        onClose={() => setRubricRound(null)}
      />

      <QuizBankModal
        open={!!quizRound}
        roundId={quizRound?.id ?? null}
        roundName={quizRound?.name}
        onClose={() => setQuizRound(null)}
      />

      <Modal
        open={!!editRound}
        onClose={() => setEditRound(null)}
        title={editRound ? `Edit deadline — ${editRound.name}` : "Edit deadline"}
      >
        <form
          onSubmit={handleSaveWindow}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.45)", margin: 0, lineHeight: 1.5 }}>
            Submissions are blocked outside this window. Leave a field empty to
            leave that side open.
          </p>
          <Input
            label="Opens (start)"
            type="datetime-local"
            value={editForm.start_date}
            onChange={(e) => setEditForm((p) => ({ ...p, start_date: e.target.value }))}
            fullWidth
          />
          <Input
            label="Deadline (end)"
            type="datetime-local"
            value={editForm.end_date}
            onChange={(e) => setEditForm((p) => ({ ...p, end_date: e.target.value }))}
            fullWidth
          />
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontSize: "0.82rem",
              color: "rgba(255,255,255,0.7)",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={editForm.reopen}
              onChange={(e) => setEditForm((p) => ({ ...p, reopen: e.target.checked }))}
              style={{ accentColor: "#e8503a" }}
            />
            Reopen teams disqualified for missing this deadline
          </label>
          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <Button type="button" variant="secondary" onClick={() => setEditRound(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={savingWindow} style={{ flex: 1 }}>
              Save Deadline
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Add Round"
      >
        <form
          onSubmit={handleCreate}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <Input
            label="Round Name *"
            value={form.name}
            onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            placeholder="e.g., Preliminary Round"
            fullWidth
            required
          />
          <Select
            label="Status"
            value={form.status}
            onChange={(e) =>
              setForm((p) => ({ ...p, status: e.target.value as RoundStatus }))
            }
            fullWidth
            options={[
              { value: "upcoming", label: "Upcoming" },
              { value: "active", label: "Active" },
              { value: "completed", label: "Completed" },
            ]}
          />
          <Input
            label="Start Date"
            type="datetime-local"
            value={form.start_date}
            onChange={(e) =>
              setForm((p) => ({ ...p, start_date: e.target.value }))
            }
            fullWidth
          />
          <Input
            label="End Date"
            type="datetime-local"
            value={form.end_date}
            onChange={(e) =>
              setForm((p) => ({ ...p, end_date: e.target.value }))
            }
            fullWidth
          />
          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={creating}
              style={{ flex: 1 }}
            >
              Create Round
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
