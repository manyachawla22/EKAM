"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { FileText, Search, CheckCircle, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { listManualPlagiarismReports, manualPlagiarismCheck } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useAutoRefresh } from "@/lib/useAutoRefresh";
import type { Report } from "@/types";
import Button from "@/components/ui/Button";

function getData(report: Report): Record<string, any> {
  return (report.data as Record<string, any>) || {};
}

export default function PlagiarismPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();

  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const [file1, setFile1] = useState<File | null>(null);
  const [file2, setFile2] = useState<File | null>(null);
  const [threshold, setThreshold] = useState("0.75");

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const data = await listManualPlagiarismReports(id);
      setReports(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load plagiarism reports");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (authLoading) return;
    if (!user || !id) {
      setLoading(false);
      return;
    }
    load();
  }, [id, authLoading, user, load]);

  useAutoRefresh(() => {
    if (user && id) load();
  });

  const handleRun = async () => {
    if (!id || !file1 || !file2) {
      toast.error("Please upload both PDFs");
      return;
    }

    setRunning(true);
    try {
      await manualPlagiarismCheck(id, file1, file2, Number(threshold));
      toast.success("Manual plagiarism check completed");
      setFile1(null);
      setFile2(null);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to run plagiarism check");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ maxWidth: "70rem", margin: "0 auto", width: "100%" }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "1rem",
          marginBottom: "2rem",
          flexWrap: "wrap",
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
              gap: "0.6rem",
            }}
          >
            <FileText size={22} color="#e8503a" />
            Plagiarism
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            Manual committee-side plagiarism verification between two uploaded PDFs.
          </p>
        </div>
      </div>

      <div
        style={{
          borderRadius: "0.75rem",
          border: "1px solid #222",
          background: "#111",
          padding: "1.25rem",
          marginBottom: "1.25rem",
          display: "grid",
          gap: "1rem",
        }}
      >
        <div style={{ display: "grid", gap: "0.75rem", gridTemplateColumns: "1fr 1fr 160px auto" }}>
          <div>
            <label style={labelStyle}>PDF 1</label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setFile1(e.target.files?.[0] || null)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>PDF 2</label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setFile2(e.target.files?.[0] || null)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>Threshold</label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div style={{ display: "flex", alignItems: "end" }}>
            <Button variant="primary" onClick={handleRun} loading={running}>
              <Search size={16} /> Check
            </Button>
          </div>
        </div>

        <div style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.45)" }}>
          Use this as a manual integrity-review tool for suspicious or disputed submissions.
        </div>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="shimmer" style={{ height: "6rem", borderRadius: "0.75rem" }} />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.75rem",
            padding: "4rem 0",
            textAlign: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              height: "3.5rem",
              width: "3.5rem",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "1rem",
              background: "#111",
              border: "1px solid #222",
            }}
          >
            <CheckCircle size={26} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)", margin: 0 }}>
            No manual plagiarism checks yet.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {reports.map((report, index) => {
            const d = getData(report);
            const suspicious = Boolean(d.suspicious);

            return (
              <motion.div
                key={report.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04 }}
                style={{
                  borderRadius: "0.75rem",
                  border: "1px solid #222",
                  background: "#111",
                  padding: "1.25rem",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "1rem",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    marginBottom: "1rem",
                  }}
                >
                  <div>
                    <h2 style={{ margin: 0, color: "#fff", fontSize: "1rem" }}>
                      {report.title}
                    </h2>
                    <p style={{ margin: "0.35rem 0 0", color: "rgba(255,255,255,0.4)", fontSize: "0.8rem" }}>
                      {(report.created_at || (report as any).generated_at)
                        ? new Date((report.created_at || (report as any).generated_at) as string).toLocaleString()
                        : "—"}
                    </p>
                  </div>

                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      padding: "0.35rem 0.7rem",
                      borderRadius: "9999px",
                      border: `1px solid ${suspicious ? "rgba(248,113,113,0.35)" : "rgba(74,222,128,0.35)"}`,
                      color: suspicious ? "#f87171" : "#4ade80",
                      background: suspicious ? "rgba(248,113,113,0.08)" : "rgba(74,222,128,0.08)",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                    }}
                  >
                    {suspicious ? <AlertTriangle size={14} /> : <CheckCircle size={14} />}
                    {suspicious ? "Suspicious" : "Not Suspicious"}
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "0.75rem",
                    marginBottom: "1rem",
                  }}
                >
                  <MiniStat label="Similarity" value={d.similarity ?? "—"} />
                  <MiniStat label="Threshold" value={d.threshold ?? "—"} />
                  <MiniStat label="File 1" value={d.file_1_name ?? "—"} />
                  <MiniStat label="File 2" value={d.file_2_name ?? "—"} />
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: any }) {
  return (
    <div
      style={{
        borderRadius: "0.75rem",
        border: "1px solid #222",
        background: "#0d0d0d",
        padding: "0.9rem 1rem",
      }}
    >
      <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#fff", wordBreak: "break-word" }}>
        {String(value)}
      </div>
      <div style={{ marginTop: "0.2rem", fontSize: "0.72rem", color: "rgba(255,255,255,0.45)" }}>
        {label}
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  marginBottom: "0.4rem",
  fontSize: "0.8rem",
  color: "rgba(255,255,255,0.55)",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  borderRadius: "0.6rem",
  border: "1px solid #222",
  background: "#0d0d0d",
  color: "#fff",
  padding: "0.75rem",
};