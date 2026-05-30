"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useRef } from "react";
import { motion } from "framer-motion";
import { Users, Search, Upload, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { listParticipants, uploadParticipantCSV, deleteParticipant } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Participant } from "@/types";
import Button from "@/components/ui/Button";

export default function ParticipantsPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const [searchFocus, setSearchFocus] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDelete = async (participantId: string) => {
    if (!id) return;
    try {
      await deleteParticipant(id, participantId);
      setParticipants((prev) => prev.filter((p) => p.id !== participantId));
      toast.success("Participant removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove participant");
    }
  };

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !id) return;
    setUploading(true);
    try {
      const result = await uploadParticipantCSV(id, file);
      toast.success(result.message || `Imported ${result.count} participants`);
      const updated = await listParticipants(id);
      setParticipants(updated);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "CSV upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  useEffect(() => {
    if (authLoading) return;
    if (!user || !id) {
      setLoading(false);
      return;
    }
    listParticipants(id)
      .then(setParticipants)
      .catch((err: Error) =>
        toast.error(err.message || "Failed to load participants")
      )
      .finally(() => setLoading(false));
  }, [id, authLoading, user]);

  const filtered = participants.filter((p) => {
    const q = search.toLowerCase();
    return (
      p.name?.toLowerCase().includes(q) ||
      p.email?.toLowerCase().includes(q) ||
      p.institution?.toLowerCase().includes(q)
    );
  });

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
            Participants
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            {participants.length} registered
          </p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: "none" }}
            onChange={handleCSVUpload}
          />
          <Button
            variant="primary"
            loading={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload size={16} /> Upload CSV
          </Button>
        </div>
      </div>

      <div
        style={{
          marginBottom: "1.5rem",
          position: "relative",
          maxWidth: "24rem",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "0.875rem",
            top: "50%",
            transform: "translateY(-50%)",
            pointerEvents: "none",
            color: "rgba(255,255,255,0.3)",
            display: "flex",
          }}
        >
          <Search size={16} />
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onFocus={() => setSearchFocus(true)}
          onBlur={() => setSearchFocus(false)}
          placeholder="Search participants..."
          style={{
            width: "100%",
            borderRadius: "0.5rem",
            border: `1px solid ${searchFocus ? "#e8503a" : "#222"}`,
            background: "#111",
            padding: "0.625rem 1rem 0.625rem 2.5rem",
            fontSize: "0.875rem",
            color: "#fff",
            outline: "none",
            transition: "all 0.2s",
            fontFamily: "inherit",
            boxSizing: "border-box",
          }}
        />
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "3.5rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
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
            <Users size={32} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>
            {search ? "No participants match your search" : "No participants yet"}
          </p>
        </div>
      ) : (
        <div
          style={{
            borderRadius: "0.75rem",
            border: "1px solid #222",
            background: "#111",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr 1fr 1fr auto",
              gap: "1rem",
              borderBottom: "1px solid #222",
              padding: "0.75rem 1.25rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "rgba(255,255,255,0.3)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>Participant</span>
            <span>Institution</span>
            <span>Skills</span>
            <span>Joined</span>
            <span />
          </div>
          {filtered.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 1fr 1fr 1fr auto",
                gap: "1rem",
                alignItems: "center",
                borderBottom: i === filtered.length - 1 ? "none" : "1px solid rgba(34,34,34,0.5)",
                padding: "0.875rem 1.25rem",
                transition: "background 0.2s",
              }}
            >
              <div style={{ minWidth: 0 }}>
                <p
                  style={{
                    fontWeight: 500,
                    color: "#fff",
                    fontSize: "0.875rem",
                    margin: 0,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {p.name || "—"}
                </p>
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.4)",
                    margin: 0,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {p.email}
                </p>
              </div>
              <span
                style={{
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.6)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {p.institution || "—"}
              </span>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "rgba(255,255,255,0.5)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {p.skills && p.skills.length > 0 ? p.skills.join(", ") : "—"}
              </span>
              <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)" }}>
                {p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}
              </span>
              <button
                onClick={() => handleDelete(p.id)}
                title="Remove participant"
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
