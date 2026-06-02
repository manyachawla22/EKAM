"use client";

import { useEffect, useState, useCallback } from "react";
import { Plus, Trash2, Sparkles, Save } from "lucide-react";
import { toast } from "sonner";
import {
  listRoundRubric,
  addRubricCriterion,
  updateRubricCriterion,
  deleteRubricCriterion,
  generateRoundRubric,
} from "@/lib/api";
import type { RubricCriterion } from "@/types";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

interface Props {
  open: boolean;
  roundId: string | null;
  roundName?: string;
  onClose: () => void;
}

const inputBase: React.CSSProperties = {
  borderRadius: "0.4rem",
  border: "1px solid #222",
  background: "#0d0d0d",
  padding: "0.4rem 0.5rem",
  fontSize: "0.85rem",
  color: "#fff",
  outline: "none",
};

export default function RubricEditorModal({ open, roundId, roundName, onClose }: Props) {
  const [criteria, setCriteria] = useState<RubricCriterion[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newMax, setNewMax] = useState(10);
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    if (!roundId) return;
    setLoading(true);
    try {
      setCriteria(await listRoundRubric(roundId));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load rubric");
    } finally {
      setLoading(false);
    }
  }, [roundId]);

  useEffect(() => {
    if (open && roundId) load();
  }, [open, roundId, load]);

  const total = criteria.reduce((s, c) => s + c.max_score, 0);

  const handleField = (id: string, patch: Partial<RubricCriterion>) =>
    setCriteria((prev) => prev.map((c) => (c.id === id ? { ...c, ...patch } : c)));

  const saveRow = async (c: RubricCriterion) => {
    setSavingId(c.id);
    try {
      await updateRubricCriterion(c.id, { name: c.name, max_score: c.max_score, description: c.description ?? undefined });
      toast.success("Saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSavingId(null);
    }
  };

  const removeRow = async (id: string) => {
    try {
      await deleteRubricCriterion(id);
      setCriteria((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  const addRow = async () => {
    if (!roundId || !newName.trim()) {
      toast.error("Criterion name is required");
      return;
    }
    setAdding(true);
    try {
      const created = await addRubricCriterion(roundId, {
        name: newName.trim(),
        max_score: newMax,
        position: criteria.length,
      });
      setCriteria((prev) => [...prev, created]);
      setNewName("");
      setNewMax(10);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add criterion");
    } finally {
      setAdding(false);
    }
  };

  const generate = async () => {
    if (!roundId) return;
    setGenerating(true);
    try {
      const next = await generateRoundRubric(roundId);
      setCriteria(next);
      toast.success("Rubric generated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to generate");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={`Rubric — ${roundName ?? "Round"}`} size="lg">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
        <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.5)", margin: 0 }}>
          Judges score each criterion; the total is the sum. Current total: <strong style={{ color: "#fff" }}>{total}</strong> points.
        </p>
        <Button variant="secondary" onClick={generate} loading={generating}>
          <Sparkles size={14} /> Generate with AI
        </Button>
      </div>

      {loading ? (
        <div className="shimmer" style={{ height: "10rem", borderRadius: "0.5rem" }} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
          {criteria.map((c) => (
            <div key={c.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <input
                value={c.name}
                onChange={(e) => handleField(c.id, { name: e.target.value })}
                style={{ ...inputBase, flex: 1 }}
              />
              <input
                type="number"
                min={0}
                value={c.max_score}
                onChange={(e) => handleField(c.id, { max_score: Number(e.target.value) || 0 })}
                style={{ ...inputBase, width: "4.5rem", textAlign: "center" }}
                title="Max points"
              />
              <button
                onClick={() => saveRow(c)}
                disabled={savingId === c.id}
                style={{ display: "flex", height: "2rem", width: "2rem", alignItems: "center", justifyContent: "center", borderRadius: "0.4rem", border: "1px solid rgba(34,197,94,0.3)", background: "transparent", color: "#4ade80", cursor: "pointer" }}
                title="Save"
              >
                <Save size={15} />
              </button>
              <button
                onClick={() => removeRow(c.id)}
                style={{ display: "flex", height: "2rem", width: "2rem", alignItems: "center", justifyContent: "center", borderRadius: "0.4rem", border: "1px solid #222", background: "transparent", color: "rgba(255,255,255,0.3)", cursor: "pointer" }}
                title="Delete"
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}

          {/* Add new criterion */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.5rem", paddingTop: "0.75rem", borderTop: "1px solid #1e1e1e" }}>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="New criterion name"
              style={{ ...inputBase, flex: 1 }}
            />
            <input
              type="number"
              min={0}
              value={newMax}
              onChange={(e) => setNewMax(Number(e.target.value) || 0)}
              style={{ ...inputBase, width: "4.5rem", textAlign: "center" }}
              title="Max points"
            />
            <button
              onClick={addRow}
              disabled={adding}
              style={{ display: "flex", height: "2rem", width: "2rem", alignItems: "center", justifyContent: "center", borderRadius: "0.4rem", border: "1px solid rgba(232,80,58,0.3)", background: "transparent", color: "#e8503a", cursor: "pointer" }}
              title="Add"
            >
              <Plus size={16} />
            </button>
            <span style={{ width: "2rem" }} />
          </div>
        </div>
      )}
    </Modal>
  );
}
