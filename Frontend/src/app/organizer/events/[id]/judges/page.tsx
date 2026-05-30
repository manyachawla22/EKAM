"use client";

export const dynamic = "force-dynamic";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Zap, UserCheck, Upload, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { listJudges, uploadJudgeCSV, autoAssignJudges, deleteJudge } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Judge } from "@/types";
import Button from "@/components/ui/Button";

export default function JudgesPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();

  const [judges, setJudges] = useState<Judge[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [autoAssigning, setAutoAssigning] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user || !id) {
      setLoading(false);
      return;
    }
    listJudges(id)
      .then(setJudges)
      .catch((err: Error) => toast.error(err.message || "Failed to load judges"))
      .finally(() => setLoading(false));
  }, [id, authLoading, user]);

  const handleDelete = async (judgeId: string) => {
    if (!id) return;
    try {
      await deleteJudge(id, judgeId);
      setJudges((prev) => prev.filter((j) => j.id !== judgeId));
      toast.success("Judge removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove judge");
    }
  };

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !id) return;
    setUploading(true);
    try {
      const result = await uploadJudgeCSV(id, file);
      toast.success(result.message || `Imported ${result.count} judges`);
      const updated = await listJudges(id);
      setJudges(updated);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "CSV upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleAutoAssign = async () => {
    if (!id) return;
    setAutoAssigning(true);
    try {
      const result = await autoAssignJudges(id, 2);
      toast.success(result.message || "Judge assignment proposed — check Approvals.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Auto-assign failed");
    } finally {
      setAutoAssigning(false);
    }
  };

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      {/* Header */}
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
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: "none" }}
            onChange={handleCSVUpload}
          />
          <Button
            variant="secondary"
            loading={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload size={16} /> Upload CSV
          </Button>
        </div>
      </div>

      {/* Auto-assign card */}
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
              CP-SAT optimally distributes judges across all teams. A proposal will be sent for your approval.
            </p>
          </div>
          <Button variant="primary" loading={autoAssigning} onClick={handleAutoAssign}>
            <Zap size={16} /> Propose Assignment
          </Button>
        </div>
      </div>

      {/* Judges list */}
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="shimmer" style={{ height: "4rem", borderRadius: "0.75rem" }} />
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
            No judges yet. Upload a CSV to add judges.
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
                <p style={{ fontWeight: 500, color: "#fff", margin: 0 }}>
                  {j.name || j.email}
                </p>
                {j.email && (
                  <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
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
              <button
                onClick={() => handleDelete(j.id)}
                title="Remove judge"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "1.75rem",
                  width: "1.75rem",
                  borderRadius: "0.375rem",
                  border: "1px solid rgba(239,68,68,0.25)",
                  background: "transparent",
                  color: "rgba(239,68,68,0.6)",
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              >
                <Trash2 size={13} />
              </button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
