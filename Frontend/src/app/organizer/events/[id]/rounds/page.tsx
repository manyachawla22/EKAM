"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, Layers, Calendar, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { listRounds, createRound, deleteRound } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Round, RoundStatus } from "@/types";
import Button from "@/components/ui/Button";
import Input, { Select } from "@/components/ui/Input";
import { RoundStatusBadge } from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";

export default function RoundsPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();

  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const [form, setForm] = useState({
    name: "",
    status: "upcoming" as RoundStatus,
    start_date: "",
    end_date: "",
  });

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

  const handleDelete = async (roundId: string) => {
    if (!id) return;
    try {
      await deleteRound(id, roundId);
      setRounds((prev) => prev.filter((r) => r.id !== roundId));
      toast.success("Round deleted");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete round");
    }
  };

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
              <button
                onClick={() => handleDelete(round.id)}
                title="Delete round"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "2rem",
                  width: "2rem",
                  borderRadius: "0.4rem",
                  border: "1px solid rgba(239,68,68,0.25)",
                  background: "transparent",
                  color: "rgba(239,68,68,0.55)",
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              >
                <Trash2 size={14} />
              </button>
            </motion.div>
          ))}
        </div>
      )}

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
