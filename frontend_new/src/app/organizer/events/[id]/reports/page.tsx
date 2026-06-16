"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { BarChart2, FileText, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { listReports, generateEventReport } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useAutoRefresh } from "@/lib/useAutoRefresh";
import type { Report } from "@/types";
import Button from "@/components/ui/Button";

function reportHtml(report: Report | null): string | null {
  if (!report?.data) return null;
  const html = (report.data as Record<string, unknown>).report_html;
  return typeof html === "string" ? html : null;
}

export default function ReportsPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [active, setActive] = useState<Report | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const data = await listReports(id);
      setReports(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load reports");
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

  const handleGenerate = async () => {
    if (!id) return;
    setGenerating(true);
    try {
      const report = await generateEventReport(id);
      toast.success("Report generated and emailed to the organizer");
      await load();
      setActive(report);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  const activeHtml = reportHtml(active);

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "1rem", marginBottom: "2rem", flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 900, fontStyle: "italic", color: "#fff", margin: 0 }}>
            Reports
          </h1>
          <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.4)" }}>
            Generate an event summary (standings, charts, participant performance). The report is stored here and emailed to the organizer.
          </p>
        </div>
        <Button variant="primary" onClick={handleGenerate} loading={generating}>
          <Sparkles size={16} /> Generate Report
        </Button>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="shimmer" style={{ height: "4rem", borderRadius: "0.75rem" }} />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem", padding: "5rem 0", textAlign: "center" }}>
          <div style={{ display: "flex", height: "4rem", width: "4rem", alignItems: "center", justifyContent: "center", borderRadius: "1rem", background: "#111", border: "1px solid #222" }}>
            <BarChart2 size={32} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>No reports yet. Generate one to get started.</p>
        </div>
      ) : (
        <div style={{ borderRadius: "0.75rem", border: "1px solid #222", background: "#111", overflow: "hidden" }}>
          {reports.map((r, i) => (
            <motion.div
              key={r.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
              style={{ display: "flex", alignItems: "center", gap: "1rem", borderBottom: i === reports.length - 1 ? "none" : "1px solid rgba(34,34,34,0.5)", padding: "0.875rem 1.25rem" }}
            >
              <FileText size={18} color="#e8503a" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: "0.875rem", fontWeight: 500, color: "#fff", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {r.title}
                </p>
                <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
                  {r.type} · {(r.created_at || r.generated_at) ? new Date((r.created_at || r.generated_at) as string).toLocaleString() : "—"}
                </p>
              </div>
              <button
                onClick={() => setActive(r)}
                style={{ fontSize: "0.75rem", fontWeight: 500, color: "#e8503a", background: "transparent", border: "1px solid rgba(232,80,58,0.3)", borderRadius: "0.5rem", padding: "0.35rem 0.75rem", cursor: "pointer" }}
              >
                View
              </button>
            </motion.div>
          ))}
        </div>
      )}

      {active && (
        <div
          onClick={() => setActive(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem", zIndex: 50 }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ width: "100%", maxWidth: "60rem", height: "85vh", background: "#0a0a0a", borderRadius: "0.75rem", border: "1px solid #222", display: "flex", flexDirection: "column", overflow: "hidden" }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0.75rem 1rem", borderBottom: "1px solid #222" }}>
              <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff" }}>{active.title}</span>
              <button onClick={() => setActive(null)} style={{ background: "transparent", border: "none", color: "rgba(255,255,255,0.5)", cursor: "pointer", display: "flex" }}>
                <X size={18} />
              </button>
            </div>
            {activeHtml ? (
              <iframe
                title={active.title}
                srcDoc={activeHtml}
                style={{ flex: 1, width: "100%", border: "none", background: "#fff" }}
              />
            ) : (
              <pre style={{ flex: 1, margin: 0, padding: "1rem", overflow: "auto", color: "rgba(255,255,255,0.7)", fontSize: "0.8rem" }}>
                {JSON.stringify(active.data ?? {}, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
