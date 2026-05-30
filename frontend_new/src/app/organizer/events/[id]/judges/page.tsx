"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, Zap, UserCheck, Mail } from "lucide-react";
import { toast } from "sonner";
import {
  listJudges,
  inviteJudge,
  listRounds,
  autoAssignJudges,
  uploadJudgesCsv,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Judge, Round } from "@/types";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Modal from "@/components/ui/Modal";
import CsvUploadButton from "@/components/ui/CsvUploadButton";

const inputBase: React.CSSProperties = {
  width: "100%",
  borderRadius: "0.5rem",
  border: "1px solid #222",
  background: "#0d0d0d",
  padding: "0.625rem 0.75rem",
  fontSize: "0.875rem",
  color: "#fff",
  outline: "none",
  fontFamily: "inherit",
  boxSizing: "border-box",
};

export default function JudgesPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();

  const [judges, setJudges] = useState<Judge[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [autoAssigning, setAutoAssigning] = useState(false);
  const [selectedRound, setSelectedRound] = useState<string>("");

  const [inviteForm, setInviteForm] = useState({
    email: "",
    name: "",
  });

  useEffect(() => {
    if (authLoading) return;
    if (!user || !id) {
      setLoading(false);
      return;
    }
    Promise.all([
      listJudges(id).catch(() => []),
      listRounds(id).catch(() => []),
    ])
      .then(([j, r]) => {
        setJudges(j);
        setRounds(r);
        if (r.length > 0) setSelectedRound(r[0].id);
      })
      .catch((err: Error) => toast.error(err.message || "Failed to load data"))
      .finally(() => setLoading(false));
  }, [id, authLoading, user]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteForm.email || !id) {
      toast.error("Email is required");
      return;
    }
    setInviting(true);
    try {
      await inviteJudge({
        email: inviteForm.email,
        event_id: id,
        name: inviteForm.name || undefined,
      });
      toast.success("Invitation sent!");
      setInviteModalOpen(false);
      setInviteForm({ email: "", name: "" });
      const updated = await listJudges(id);
      setJudges(updated);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to send invitation"
      );
    } finally {
      setInviting(false);
    }
  };

  const handleAutoAssign = async () => {
    if (!selectedRound || !id) {
      toast.error("Please select a round first");
      return;
    }
    setAutoAssigning(true);
    try {
      const result = await autoAssignJudges(selectedRound, 2);
      if (result.success) {
        toast.success(`Auto-assigned judges to all teams!`);
        const updated = await listJudges(id);
        setJudges(updated);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Auto-assign failed");
    } finally {
      setAutoAssigning(false);
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
            Judges
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            {judges.length} judge{judges.length !== 1 ? "s" : ""} assigned
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          <CsvUploadButton
            label="Bulk Import CSV"
            disabled={!id}
            onUpload={(file) => uploadJudgesCsv(id, file)}
            onUploaded={async () => {
              if (!id) return;
              const updated = await listJudges(id).catch(() => []);
              setJudges(updated);
            }}
          />
          <Button variant="primary" onClick={() => setInviteModalOpen(true)}>
            <Plus size={16} /> Invite Judge
          </Button>
        </div>
      </div>

      {rounds.length > 0 && (
        <div
          style={{
            marginBottom: "2rem",
            borderRadius: "0.75rem",
            border: "1px solid rgba(232,80,58,0.2)",
            background: "rgba(232,80,58,0.05)",
            padding: "1.25rem",
          }}
        >
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "1rem",
            }}
          >
            <div>
              <h3
                style={{
                  fontWeight: 600,
                  color: "#fff",
                  margin: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <Zap size={16} color="#e8503a" />
                Auto-Assign Judges
              </h3>
              <p
                style={{
                  marginTop: "0.25rem",
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.5)",
                }}
              >
                Automatically distribute judges across all teams for a round.
              </p>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                flexWrap: "wrap",
              }}
            >
              <select
                value={selectedRound}
                onChange={(e) => setSelectedRound(e.target.value)}
                style={{ ...inputBase, width: "auto", padding: "0.5rem 0.75rem" }}
              >
                {rounds.map((r) => (
                  <option key={r.id} value={r.id} style={{ background: "#111" }}>
                    {r.name}
                  </option>
                ))}
              </select>
              <Button
                variant="primary"
                loading={autoAssigning}
                onClick={handleAutoAssign}
              >
                <Zap size={16} /> Auto-Assign
              </Button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "4rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : judges.length === 0 ? (
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
            <UserCheck size={32} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>
            No judges yet. Invite judges to this event.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {judges.map((j, i) => (
            <motion.div
              key={j.id}
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
                padding: "1rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  height: "2.5rem",
                  width: "2.5rem",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "9999px",
                  background: "rgba(168,85,247,0.15)",
                  color: "#c084fc",
                  flexShrink: 0,
                }}
              >
                <UserCheck size={20} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p
                  style={{
                    fontWeight: 500,
                    color: "#fff",
                    margin: 0,
                  }}
                >
                  {j.name || j.email}
                </p>
                {j.email && (
                  <p
                    style={{
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.4)",
                      margin: 0,
                    }}
                  >
                    {j.email}
                  </p>
                )}
              </div>
              {j.institution && (
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.4)",
                    background: "#222",
                    borderRadius: "9999px",
                    padding: "0.25rem 0.625rem",
                  }}
                >
                  {j.institution}
                </span>
              )}
            </motion.div>
          ))}
        </div>
      )}

      <Modal
        open={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        title="Invite Judge"
      >
        <form
          onSubmit={handleInvite}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <div
            style={{
              borderRadius: "0.5rem",
              background: "rgba(59,130,246,0.1)",
              border: "1px solid rgba(59,130,246,0.2)",
              padding: "0.75rem 1rem",
              fontSize: "0.875rem",
              color: "#60a5fa",
              display: "flex",
              alignItems: "flex-start",
              gap: "0.5rem",
            }}
          >
            <Mail size={16} style={{ marginTop: "0.125rem", flexShrink: 0 }} />
            An invitation email will be sent to the judge with access instructions.
          </div>
          <Input
            label="Email Address *"
            type="email"
            value={inviteForm.email}
            onChange={(e) =>
              setInviteForm((p) => ({ ...p, email: e.target.value }))
            }
            placeholder="judge@example.com"
            fullWidth
            required
          />
          <Input
            label="Name (optional)"
            value={inviteForm.name}
            onChange={(e) =>
              setInviteForm((p) => ({ ...p, name: e.target.value }))
            }
            placeholder="Judge's full name"
            fullWidth
          />
          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setInviteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={inviting}
              style={{ flex: 1 }}
            >
              Send Invitation
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
