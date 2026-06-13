"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Users, Layers, Send, UserCheck, BarChart2, Edit2, ArrowLeft,
  Trophy, Trash2, Save, ShieldCheck, AlertTriangle, CheckCircle2, Award, Plus,
} from "lucide-react";
import { toast } from "sonner";
import {
  getEvent,
  getOrganizerDashboard,
  listRounds,
  listThemes,
  createTheme,
  deleteTheme,
  updateEvent,
  deleteEvent,
  autoFormTeams,
  autoAssignJudges,
  getPipelineState,
  advancePipeline,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event, EventStatus, Round, OrganizerDashboard, Theme, PipelineState } from "@/types";
import { EventStatusBadge, EventStageBadge } from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import DynamicPipeline from "@/components/pipeline/DynamicPipeline";
import RegistrationFormEditor from "@/components/organizer/RegistrationFormEditor";

const STATUSES: EventStatus[] = ["draft", "active", "completed", "archived"];

const card: React.CSSProperties = {
  borderRadius: "0.75rem",
  border: "1px solid #222",
  background: "#111",
  padding: "1.5rem",
};

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

const formLabel: React.CSSProperties = {
  display: "block",
  marginBottom: "0.375rem",
  fontSize: "0.875rem",
  fontWeight: 500,
  color: "rgba(255,255,255,0.7)",
};

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [event, setEvent] = useState<Event | null>(null);
  const [dashboard, setDashboard] = useState<OrganizerDashboard | null>(null);
  const [pipeline, setPipeline] = useState<PipelineState | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [themeName, setThemeName] = useState("");
  const [themeDesc, setThemeDesc] = useState("");
  const [themeSkills, setThemeSkills] = useState("");
  const [themeBusy, setThemeBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "", type: "", description: "",
    status: "draft" as EventStatus,
    max_participants: 100,
  });

  // Stage action state
  const [teamSize, setTeamSize] = useState(4);
  const [selectedRound, setSelectedRound] = useState("");
  const [cutoffScore, setCutoffScore] = useState(60);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchAll = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [ev, dash, rds, thms, pipe] = await Promise.all([
        getEvent(id),
        getOrganizerDashboard(id).catch(() => null),
        listRounds(id).catch(() => [] as Round[]),
        listThemes(id).catch(() => [] as Theme[]),
        getPipelineState(id).catch(() => null),
      ]);
      setEvent(ev);
      setDashboard(dash);
      setRounds(rds);
      setThemes(thms);
      setPipeline(pipe);
      setEditForm({
        name: ev.name, type: ev.type, description: ev.description,
        status: ev.status, max_participants: ev.max_participants,
      });
      if (rds.length > 0) setSelectedRound(rds[0].id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load event");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authLoading) return;
    if (!user || !id) return;
    fetchAll();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, authLoading, user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await updateEvent(id, editForm);
      setEvent(updated);
      setEditOpen(false);
      toast.success("Event updated!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  };

  const handleAddTheme = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!themeName.trim()) { toast.error("Theme name is required"); return; }
    setThemeBusy(true);
    try {
      const required_skills = themeSkills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await createTheme(id, {
        name: themeName.trim(),
        description: themeDesc.trim() || undefined,
        required_skills: required_skills.length ? required_skills : undefined,
      });
      setThemeName("");
      setThemeDesc("");
      setThemeSkills("");
      setThemes(await listThemes(id).catch(() => themes));
      toast.success("Theme added");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add theme");
    } finally {
      setThemeBusy(false);
    }
  };

  const handleDeleteTheme = async (themeId: string) => {
    setThemeBusy(true);
    try {
      await deleteTheme(id, themeId);
      setThemes((prev) => prev.filter((t) => t.id !== themeId));
      toast.success("Theme removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove theme");
    } finally {
      setThemeBusy(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteEvent(id);
      toast.success("Event deleted");
      router.push("/organizer/events");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
    }
  };

  const handleAutoFormTeams = async () => {
    setActionLoading(true);
    try {
      const result = await autoFormTeams(id, teamSize);
      toast.success(result.message || "Team formation proposed — review in Approvals.");
      fetchAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Auto-form failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAutoAssignJudges = async () => {
    setActionLoading(true);
    try {
      const result = await autoAssignJudges(id, 2);
      toast.success(result.message || "Judge assignment proposed — review in Approvals.");
      fetchAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Auto-assign failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Advance the *dynamic* pipeline by one real step (team_formation →
  // theme_selection → judge_assignment → per-round steps → …) instead of the
  // coarse, hardcoded stage list — so no intermediate stage is skipped.
  const handleAdvancePipeline = async (cutoff = 0) => {
    setActionLoading(true);
    try {
      const res = await advancePipeline(id, cutoff);
      toast.success(res.message || "Pipeline advanced.");
      await fetchAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to advance pipeline");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div className="shimmer" style={{ height: "2rem", width: "12rem", borderRadius: "0.5rem" }} />
        <div className="shimmer" style={{ height: "10rem", borderRadius: "0.75rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px,1fr))", gap: "1rem" }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="shimmer" style={{ height: "6rem", borderRadius: "0.75rem" }} />
          ))}
        </div>
      </div>
    );
  }

  if (!event) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem", padding: "5rem 0", textAlign: "center" }}>
        <p style={{ color: "rgba(255,255,255,0.4)" }}>Event not found</p>
        <button onClick={() => router.back()} style={{ fontSize: "0.875rem", color: "#e8503a", background: "transparent", border: "none", cursor: "pointer" }}>
          Go back
        </button>
      </div>
    );
  }

  // Dynamic-pipeline position drives the stage actions so we follow the real
  // per-round steps instead of the coarse, hardcoded stage list.
  const pipeSteps = pipeline?.steps ?? [];
  const activeStep = pipeSteps.find((s) => s.status === "active") ?? null;
  const activeStepId = activeStep?.id ?? "";
  const nextStep = pipeline?.next_step
    ? pipeSteps.find((s) => s.id === pipeline.next_step) ?? null
    : null;
  // Steps whose advance involves a scoring cutoff / elimination — those are
  // driven by the cutoff control (and auto-proposed for approval), not the
  // one-click direct advance.
  const isScoringStep =
    activeStepId.endsWith(":advancement") || activeStepId === "winner_announcement";

  // Stats from dashboard
  const stats = dashboard?.stats ?? {
    total_participants: 0, total_teams: 0, total_submissions: 0,
    total_judges: 0, pending_approvals: 0,
  };

  const statCards = [
    { label: "Participants", value: stats.total_participants, color: "#6366f1", href: `/organizer/events/${id}/participants`, icon: <Users size={18} /> },
    { label: "Teams", value: stats.total_teams, color: "#f59e0b", href: `/organizer/events/${id}/teams`, icon: <Trophy size={18} /> },
    { label: "Judges", value: stats.total_judges, color: "#38bdf8", href: `/organizer/events/${id}/judges`, icon: <UserCheck size={18} /> },
    { label: "Submissions", value: stats.total_submissions, color: "#22c55e", href: `/organizer/events/${id}/submissions`, icon: <Send size={18} /> },
    { label: "Pending Approvals", value: stats.pending_approvals, color: "#f59e0b", href: `/organizer/events/${id}/approvals`, icon: <ShieldCheck size={18} /> },
  ];

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <button
        onClick={() => router.push("/organizer/events")}
        style={{ marginBottom: "1.25rem", display: "inline-flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.4)", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
      >
        <ArrowLeft size={16} /> All events
      </button>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

        {/* Event header */}
        <div style={card}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ marginBottom: "0.75rem", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.5rem" }}>
                <EventStatusBadge status={event.status} />
                <EventStageBadge stage={event.stage} />
                <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)" }}>#{event.hash?.slice(0, 8)}</span>
              </div>
              <h1 style={{ fontSize: "1.5rem", fontWeight: 900, fontStyle: "italic", color: "#fff", margin: 0 }}>{event.name}</h1>
              <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", fontWeight: 500, color: "#e8503a" }}>{event.type}</p>
              <p style={{ marginTop: "0.75rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.5)", lineHeight: 1.6 }}>{event.description}</p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
              <button onClick={() => setEditOpen(true)} title="Edit event" style={{ display: "flex", height: "2.25rem", width: "2.25rem", alignItems: "center", justifyContent: "center", borderRadius: "0.5rem", border: "1px solid #222", background: "transparent", color: "rgba(255,255,255,0.4)", cursor: "pointer" }}>
                <Edit2 size={16} />
              </button>
              <button onClick={() => setDeleteOpen(true)} title="Delete event" style={{ display: "flex", height: "2.25rem", width: "2.25rem", alignItems: "center", justifyContent: "center", borderRadius: "0.5rem", border: "1px solid #222", background: "transparent", color: "rgba(255,255,255,0.4)", cursor: "pointer" }}>
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "1rem" }}>
          {statCards.map((stat) => (
            <Link key={stat.label} href={stat.href}>
              <motion.div
                whileHover={{ y: -2 }}
                style={{ display: "flex", alignItems: "center", gap: "1rem", borderRadius: "0.75rem", border: "1px solid #222", background: "#111", padding: "1.25rem", cursor: "pointer" }}
              >
                <div style={{ display: "flex", height: "2.5rem", width: "2.5rem", alignItems: "center", justifyContent: "center", borderRadius: "0.75rem", background: `${stat.color}20`, color: stat.color }}>
                  {stat.icon}
                </div>
                <div>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#fff", margin: 0 }}>{stat.value}</p>
                  <p style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>{stat.label}</p>
                </div>
              </motion.div>
            </Link>
          ))}
        </div>

        {/* Event pipeline + stage action */}
        <div style={card}>
          <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "1rem" }}>
            Event Pipeline
          </p>

          {/* Single dynamic, per-round pipeline (adapts to the number of rounds). */}
          <DynamicPipeline eventId={id} />

          {/* Active stage action — driven by the dynamic pipeline's current step */}
          <div style={{ marginTop: "1.25rem", padding: "1rem", borderRadius: "0.5rem", background: "rgba(232,80,58,0.06)", border: "1px solid rgba(232,80,58,0.12)" }}>
            <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "#e8503a", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "0.75rem" }}>
              Active Stage: {activeStep?.label ?? event.stage.replace("_", " ")}
            </p>
            {activeStepId === "registration" && (
              <Link href={`/organizer/events/${id}/participants`} style={{ fontSize: "0.875rem", color: "#6366f1", textDecoration: "underline" }}>
                View Participants →
              </Link>
            )}
            {activeStepId === "team_formation" && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <label style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>Team Size:</label>
                <input type="number" min={2} max={10} value={teamSize} onChange={(e) => setTeamSize(Number(e.target.value))}
                  style={{ ...inputBase, width: "5rem" }} />
                <Button variant="primary" onClick={handleAutoFormTeams} loading={actionLoading}>
                  Run CP-SAT Team Formation
                </Button>
              </div>
            )}
            {activeStepId === "theme_selection" && (
              <p style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.6)", margin: 0 }}>
                Waiting for teams to pick their theme & team name.{" "}
                <Link href={`/organizer/events/${id}/teams`} style={{ color: "#6366f1", textDecoration: "underline" }}>
                  View Teams →
                </Link>
              </p>
            )}
            {activeStepId === "judge_assignment" && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <label style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>Auto-Assign Judges</label>
                <Button variant="primary" onClick={handleAutoAssignJudges} loading={actionLoading}>
                  Run CP-SAT Judge Assignment
                </Button>
              </div>
            )}
            {activeStepId.endsWith(":submission") && (
              <p style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.6)", margin: 0 }}>
                Waiting for teams to submit for this round.{" "}
                <Link href={`/organizer/events/${id}/submissions`} style={{ color: "#6366f1", textDecoration: "underline" }}>
                  View Submissions →
                </Link>
              </p>
            )}
            {activeStepId.endsWith(":evaluation") && (
              <p style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.6)", margin: 0 }}>
                Waiting for judges to finish evaluating this round.{" "}
                <Link href={`/organizer/events/${id}/submissions`} style={{ color: "#6366f1", textDecoration: "underline" }}>
                  View Submissions →
                </Link>
              </p>
            )}
            {isScoringStep && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <label style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>Qualifying cutoff:</label>
                <input type="number" min={0} max={100} value={cutoffScore} onChange={(e) => setCutoffScore(Number(e.target.value))}
                  style={{ ...inputBase, width: "5rem" }} />
                <Button variant="primary" onClick={() => handleAdvancePipeline(cutoffScore)} loading={actionLoading}>
                  Advance to {nextStep?.label ?? "next step"} →
                </Button>
                <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.4)" }}>
                  Teams at or above the cutoff advance; the rest are eliminated.
                </span>
              </div>
            )}
            {activeStepId === "completed" && (
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <Link href={`/organizer/events/${id}/leaderboard`} style={{ fontSize: "0.875rem", color: "#6366f1", textDecoration: "underline" }}>View Leaderboard →</Link>
                <Link href={`/organizer/events/${id}/reports`} style={{ fontSize: "0.875rem", color: "#6366f1", textDecoration: "underline" }}>Generate Report →</Link>
              </div>
            )}

            {/* Direct advance — moves the dynamic pipeline forward by one real
                step. Hidden for scoring steps (handled by the cutoff control
                above) and once the pipeline is complete. */}
            {nextStep && !isScoringStep && (
              <div style={{ marginTop: "0.875rem", paddingTop: "0.875rem", borderTop: "1px solid rgba(232,80,58,0.15)", display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <span style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.45)" }}>
                  {pipeline?.ready_to_advance ? "This step is complete." : "Done with this step?"}
                </span>
                <Button variant="secondary" onClick={() => handleAdvancePipeline(0)} loading={actionLoading}>
                  Advance to {nextStep.label} →
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Themes / Tracks */}
        <div style={card}>
          <h2 style={{ fontSize: "0.875rem", fontWeight: 700, color: "#fff", margin: "0 0 0.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Layers size={16} color="#e8503a" /> Themes / Tracks
          </h2>
          <p style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.4)", margin: "0 0 1rem" }}>
            Participants choose from these themes for their team. Add or remove them anytime.
          </p>

          {themes.length === 0 ? (
            <p style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.35)", margin: "0 0 1rem" }}>
              No themes yet. Add one below.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1rem" }}>
              {themes.map((t) => (
                <div key={t.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.625rem 0.75rem", borderRadius: "0.5rem", background: "rgba(255,255,255,0.03)", border: "1px solid #1e1e1e" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", margin: 0 }}>{t.name}</p>
                    {t.description && <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>{t.description}</p>}
                    {(t.required_skills?.length ?? 0) > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginTop: "0.4rem" }}>
                        {t.required_skills!.map((skill) => (
                          <span
                            key={skill}
                            style={{
                              fontSize: "0.68rem",
                              fontWeight: 500,
                              color: "#e8503a",
                              background: "rgba(232,80,58,0.1)",
                              border: "1px solid rgba(232,80,58,0.25)",
                              borderRadius: "9999px",
                              padding: "0.1rem 0.5rem",
                            }}
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteTheme(t.id)}
                    disabled={themeBusy}
                    title="Delete theme"
                    style={{ display: "flex", height: "2rem", width: "2rem", flexShrink: 0, alignItems: "center", justifyContent: "center", borderRadius: "0.5rem", border: "1px solid #222", background: "transparent", color: "rgba(255,255,255,0.35)", cursor: themeBusy ? "default" : "pointer" }}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={handleAddTheme} style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
            <input
              value={themeName}
              onChange={(e) => setThemeName(e.target.value)}
              placeholder="Theme name — e.g., AI/ML"
              style={{ ...inputBase, flex: "2 1 12rem", width: "auto" }}
            />
            <input
              value={themeDesc}
              onChange={(e) => setThemeDesc(e.target.value)}
              placeholder="Description (optional)"
              style={{ ...inputBase, flex: "3 1 14rem", width: "auto" }}
            />
            <input
              value={themeSkills}
              onChange={(e) => setThemeSkills(e.target.value)}
              placeholder="Required skills — comma separated (e.g. React, ML)"
              title="Skills judges should have to evaluate this theme — used for judge mapping"
              style={{ ...inputBase, flex: "3 1 14rem", width: "auto" }}
            />
            <Button type="submit" variant="primary" loading={themeBusy}>
              <Plus size={16} /> Add Theme
            </Button>
          </form>
        </div>

        {/* Public registration form editor (approval-gated) */}
        <RegistrationFormEditor eventId={id} initialFields={event.registration_form_fields} />

        {/* Pending approvals */}
        {(dashboard?.pending_approvals ?? []).length > 0 && (
          <div style={card}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
              <h2 style={{ fontSize: "0.875rem", fontWeight: 700, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <ShieldCheck size={16} color="#fbbf24" /> Pending Approvals
              </h2>
              <Link href={`/organizer/events/${id}/approvals`} style={{ fontSize: "0.75rem", color: "#e8503a", textDecoration: "none" }}>View all →</Link>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {(dashboard?.pending_approvals ?? []).slice(0, 3).map((ap) => (
                <div key={ap.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.625rem 0.75rem", borderRadius: "0.375rem", background: "rgba(255,255,255,0.03)" }}>
                  <span style={{ flex: 1, fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", textTransform: "capitalize" }}>
                    {ap.request_type.replace("_", " ")}
                  </span>
                  <span style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.35)" }}>
                    {new Date(ap.requested_at).toLocaleDateString()}
                  </span>
                  <span style={{ fontSize: "0.65rem", padding: "0.15rem 0.5rem", borderRadius: "9999px", background: "rgba(251,191,36,0.12)", color: "#fbbf24", fontWeight: 600 }}>
                    {ap.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent anomalies */}
        {(dashboard?.anomalies ?? []).length > 0 && (
          <div style={card}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
              <h2 style={{ fontSize: "0.875rem", fontWeight: 700, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <AlertTriangle size={16} color="#f87171" /> Recent Anomalies
              </h2>
              <Link href={`/organizer/events/${id}/anomalies`} style={{ fontSize: "0.75rem", color: "#e8503a", textDecoration: "none" }}>View all →</Link>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {(dashboard?.anomalies ?? []).slice(0, 3).map((an) => (
                <div key={an.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.625rem 0.75rem", borderRadius: "0.375rem", background: "rgba(255,255,255,0.03)" }}>
                  <span style={{ flex: 1, fontSize: "0.8rem", color: "rgba(255,255,255,0.7)" }}>{an.description}</span>
                  <span style={{ fontSize: "0.7rem", color: "#f87171", fontWeight: 600 }}>
                    Severity: {(an.severity * 10).toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Rounds overview */}
        {(dashboard?.rounds ?? rounds).length > 0 && (
          <div style={card}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
              <h2 style={{ fontSize: "0.875rem", fontWeight: 700, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Layers size={16} color="#6366f1" /> Rounds Overview
              </h2>
              <Link href={`/organizer/events/${id}/rounds`} style={{ fontSize: "0.75rem", color: "#e8503a", textDecoration: "none" }}>Manage →</Link>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {(dashboard?.rounds ?? rounds).map((r) => (
                <div key={r.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.625rem 0.75rem", borderRadius: "0.375rem", background: "rgba(255,255,255,0.03)" }}>
                  <span style={{ flex: 1, fontSize: "0.8rem", color: "#fff", fontWeight: 500 }}>{r.name}</span>
                  <span style={{
                    fontSize: "0.65rem", fontWeight: 700, padding: "0.15rem 0.5rem", borderRadius: "9999px",
                    background: r.status === "active" ? "rgba(34,197,94,0.12)" : r.status === "upcoming" ? "rgba(251,191,36,0.12)" : "rgba(148,163,184,0.12)",
                    color: r.status === "active" ? "#4ade80" : r.status === "upcoming" ? "#fbbf24" : "#94a3b8",
                  }}>
                    {r.status}
                  </span>
                  <Link href={`/organizer/events/${id}/leaderboard`} style={{ fontSize: "0.7rem", color: "#6366f1", textDecoration: "none", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    <Award size={12} /> Leaderboard
                  </Link>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div>
          <h2 style={{ marginBottom: "0.75rem", fontSize: "0.75rem", fontWeight: 600, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Quick Access
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: "0.75rem" }}>
            {[
              { label: "Rounds", icon: <Layers size={18} />, href: `/organizer/events/${id}/rounds` },
              { label: "Participants", icon: <Users size={18} />, href: `/organizer/events/${id}/participants` },
              { label: "Teams", icon: <Trophy size={18} />, href: `/organizer/events/${id}/teams` },
              { label: "Judges", icon: <UserCheck size={18} />, href: `/organizer/events/${id}/judges` },
              { label: "Submissions", icon: <Send size={18} />, href: `/organizer/events/${id}/submissions` },
              { label: "Leaderboard", icon: <Award size={18} />, href: `/organizer/events/${id}/leaderboard` },
              { label: "Approvals", icon: <ShieldCheck size={18} />, href: `/organizer/events/${id}/approvals` },
              { label: "Reports", icon: <BarChart2 size={18} />, href: `/organizer/events/${id}/reports` },
            ].map((a) => (
              <Link key={a.label} href={a.href}>
                <motion.div whileHover={{ y: -2 }} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem", borderRadius: "0.75rem", border: "1px solid #222", background: "#111", padding: "1rem", cursor: "pointer", textAlign: "center" }}>
                  <span style={{ color: "#e8503a", display: "flex" }}>{a.icon}</span>
                  <span style={{ fontSize: "0.7rem", fontWeight: 500, color: "rgba(255,255,255,0.65)" }}>{a.label}</span>
                </motion.div>
              </Link>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Edit modal (no stage field) */}
      <Modal open={editOpen} onClose={() => setEditOpen(false)} title="Edit Event" size="lg">
        <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <Input label="Event Name *" value={editForm.name} onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))} fullWidth required />
          <Input label="Type" value={editForm.type} onChange={(e) => setEditForm((p) => ({ ...p, type: e.target.value }))} fullWidth />
          <div>
            <label style={formLabel}>Description</label>
            <textarea value={editForm.description} onChange={(e) => setEditForm((p) => ({ ...p, description: e.target.value }))} rows={3} style={{ ...inputBase, resize: "vertical", minHeight: "5rem" }} />
          </div>
          <div>
            <label style={formLabel}>Status</label>
            <select value={editForm.status} onChange={(e) => setEditForm((p) => ({ ...p, status: e.target.value as EventStatus }))} style={inputBase}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <Input label="Max Participants" type="number" value={String(editForm.max_participants)} onChange={(e) => setEditForm((p) => ({ ...p, max_participants: parseInt(e.target.value) || 0 }))} fullWidth />
          <p style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>
            Manage themes from the “Themes / Tracks” section on the event page.
          </p>
          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <Button type="button" variant="secondary" onClick={() => setEditOpen(false)}>Cancel</Button>
            <Button type="submit" variant="primary" loading={saving} style={{ flex: 1 }}>
              <Save size={16} /> Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete modal */}
      <Modal open={deleteOpen} onClose={() => setDeleteOpen(false)} title="Delete Event" size="sm">
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.6)", margin: 0 }}>
            Are you sure you want to delete <span style={{ fontWeight: 600, color: "#fff" }}>{event?.name}</span>? This cannot be undone.
          </p>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <Button variant="secondary" onClick={() => setDeleteOpen(false)} style={{ flex: 1 }}>Cancel</Button>
            <Button variant="danger" loading={deleting} onClick={handleDelete} style={{ flex: 1 }}>
              <Trash2 size={16} /> Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
