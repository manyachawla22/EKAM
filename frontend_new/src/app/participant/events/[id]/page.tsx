"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Users, Trophy, Send, Plus, Trash2, Bell, Clock, CheckCircle2, Award, FileText, Upload,
} from "lucide-react";
import { toast } from "sonner";
import {
  getEvent,
  getParticipantDashboard,
  registerParticipant,
  listRounds,
  listTeams,
  listParticipants,
  uploadSubmission,
  getLeaderboard,
  markNotificationRead,
  listThemes,
  getTeamPreferences,
  submitTeamPreference,
  uploadSubmissionFile,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event, Round, Team, ParticipantDashboard, Submission, Theme, TeamPreference } from "@/types";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { EventStatusBadge, EventStageBadge } from "@/components/ui/Badge";
import Navbar from "@/components/layout/Navbar";
import TeamDetailModal from "@/components/ui/TeamDetailModal";
import DynamicPipeline from "@/components/pipeline/DynamicPipeline";
import MyMatchesCard from "@/components/bracket/MyMatchesCard";
import QuizPaperCard from "@/components/quiz/QuizPaperCard";
import { getPipelineState } from "@/lib/api";

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
};

const STAGES = ["registration", "team_formation", "submission", "evaluation", "results", "completed"] as const;

const STAGE_MESSAGES: Record<string, string> = {
  registration: "Registration is open. Fill your profile to join.",
  team_formation: "Teams are being formed by the organizer.",
  submission: "Submission phase is open. Upload your project.",
  evaluation: "Judges are reviewing your submission.",
  results: "Results are being finalized.",
  completed: "Event complete. Check the final leaderboard.",
};

function StagePipeline({ currentStage }: { currentStage: string }) {
  const activeIdx = STAGES.indexOf(currentStage as typeof STAGES[number]);
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
        {STAGES.map((stage, i) => {
          const isPast = i < activeIdx;
          const isActive = i === activeIdx;
          const isFuture = i > activeIdx;
          return (
            <div key={stage} style={{ display: "flex", alignItems: "center", flex: i < STAGES.length - 1 ? 1 : undefined }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.375rem" }}>
                <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {isActive && (
                    <div style={{
                      position: "absolute", width: "24px", height: "24px", borderRadius: "9999px",
                      border: "2px solid #e8503a", opacity: 0.5,
                      animation: "pulse 2s infinite",
                    }} />
                  )}
                  <div style={{
                    width: "14px", height: "14px", borderRadius: "9999px", flexShrink: 0,
                    background: isPast ? "#4ade80" : isActive ? "#e8503a" : "#333",
                    border: `2px solid ${isPast ? "#4ade80" : isActive ? "#e8503a" : "#555"}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    {isPast && <CheckCircle2 size={8} color="#0a0a0a" />}
                  </div>
                </div>
                <span style={{
                  fontSize: "0.65rem", fontWeight: isActive ? 700 : 500,
                  color: isActive ? "#e8503a" : isPast ? "#4ade80" : "rgba(255,255,255,0.35)",
                  textAlign: "center", maxWidth: "60px",
                  textTransform: "capitalize",
                }}>
                  {stage.replace("_", " ")}
                </span>
              </div>
              {i < STAGES.length - 1 && (
                <div style={{
                  flex: 1, height: "2px", minWidth: "12px",
                  background: i < activeIdx ? "#4ade80" : "#333",
                  margin: "0 0.25rem", marginBottom: "1.25rem",
                }} />
              )}
            </div>
          );
        })}
      </div>
      <p style={{
        marginTop: "0.75rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.5)",
        textAlign: "center", fontStyle: "italic",
      }}>
        {STAGE_MESSAGES[currentStage] ?? ""}
      </p>
    </div>
  );
}

export default function ParticipantEventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { profile, loading: authLoading } = useAuth();

  const [event, setEvent] = useState<Event | null>(null);
  const [dashboard, setDashboard] = useState<ParticipantDashboard | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [myParticipantId, setMyParticipantId] = useState<string | null>(null);
  const [registeredCount, setRegisteredCount] = useState(0);
  const [leaderboard, setLeaderboard] = useState<Submission[]>([]);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [preferences, setPreferences] = useState<TeamPreference[]>([]);
  const [loading, setLoading] = useState(true);
  const [teamModalOpen, setTeamModalOpen] = useState(false);
  const [dismissedNotifs, setDismissedNotifs] = useState<Set<string>>(new Set());
  const [eliminatedTeamIds, setEliminatedTeamIds] = useState<string[]>([]);
  const [closedRoundIds, setClosedRoundIds] = useState<string[]>([]);

  // Registration form
  const [registering, setRegistering] = useState(false);
  const [regForm, setRegForm] = useState({ institution: "", skills: "", gender: "", age: "", phone: "" });

  // Submission form
  const [submitting, setSubmitting] = useState(false);
  const [selectedRound, setSelectedRound] = useState("");
  const [attachments, setAttachments] = useState<string[]>([""]);
  const [pdfFiles, setPdfFiles] = useState<File[]>([]);

  // Theme preference
  const [showPrefForm, setShowPrefForm] = useState(false);
  const [prefName, setPrefName] = useState("");
  const [prefThemeId, setPrefThemeId] = useState("");
  const [submittingPref, setSubmittingPref] = useState(false);

  const registered = !!dashboard?.team;
  const myTeam = registered && dashboard?.team
    ? teams.find((t) => t.id === dashboard.team!.id) ?? null
    : null;
  const isEliminated = !!(dashboard?.team && eliminatedTeamIds.includes(dashboard.team.id));

  const fetchAll = useCallback(async (initial = false) => {
    // Clear the skeleton if we can't load yet (e.g. profile not ready), so a
    // refresh before auth resolves doesn't get stuck on the loading state.
    if (!id || !profile) { if (initial) setLoading(false); return; }
    if (initial) setLoading(true);
    try {
      // Load everything independent in parallel — much faster than the previous
      // chain of sequential round-trips (matters most on a cold backend).
      const [ev, roundsData, teamsData, dash, parts, themesData, pipeline] = await Promise.all([
        getEvent(id),
        listRounds(id).catch(() => [] as Round[]),
        listTeams(id).catch(() => [] as Team[]),
        getParticipantDashboard(id).catch(() => null),
        listParticipants(id).catch(() => []),
        listThemes(id).catch(() => [] as Theme[]),
        getPipelineState(id).catch(() => null),
      ]);
      setEvent(ev);
      setRounds(roundsData);
      setTeams(teamsData);
      setDashboard(dash);
      setThemes(themesData);
      setEliminatedTeamIds(pipeline?.eliminated_team_ids ?? []);
      setClosedRoundIds(pipeline?.closed_submission_round_ids ?? []);

      // Find participant id for this user
      setRegisteredCount(parts.length);
      const me = parts.find((p) => (p.email || "").toLowerCase() === (profile.email || "").toLowerCase());
      setMyParticipantId(me?.id ?? null);

      // Team preferences (depends on the team id from the dashboard)
      if (dash?.team?.id) {
        const prefs = await getTeamPreferences(id, dash.team.id).catch(() => [] as TeamPreference[]);
        setPreferences(prefs);
        // Init preference form
        const myPref = prefs.find((p) => p.participant_id === me?.id);
        setPrefName(myPref?.preferred_name ?? dash.team.name ?? "");
        setPrefThemeId(myPref?.preferred_theme_id ?? "");
      }

      // Leaderboard for results/completed stages
      if (ev.stage === "results" || ev.stage === "completed") {
        if (roundsData.length > 0) {
          const lb = await getLeaderboard(roundsData[roundsData.length - 1].id).catch(() => [] as Submission[]);
          setLeaderboard(lb);
        }
      }
    } catch (err) {
      if (initial) toast.error(err instanceof Error ? err.message : "Failed to load event");
    } finally {
      if (initial) setLoading(false);
    }
  }, [id, profile]);

  useEffect(() => { fetchAll(true); }, [fetchAll]);
  useEffect(() => {
    const onFocus = () => fetchAll(false);
    window.addEventListener("focus", onFocus);
    // Poll so organizer-driven changes (team formation, stage advance, scores)
    // show up without a manual refresh. Pauses while the tab is hidden.
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") fetchAll(false);
    }, 12000);
    return () => {
      window.removeEventListener("focus", onFocus);
      clearInterval(interval);
    };
  }, [fetchAll]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) { toast.error("Please log in first"); return; }
    setRegistering(true);
    try {
      await registerParticipant({
        name: profile.name || profile.email,
        email: profile.email,
        event_id: id,
        institution: regForm.institution || undefined,
        skills: regForm.skills ? regForm.skills.split(",").map((s) => s.trim()).filter(Boolean) : [],
        gender: regForm.gender || undefined,
        age: regForm.age ? parseInt(regForm.age) : undefined,
        phone: regForm.phone || undefined,
      });
      toast.success("Registered successfully!");
      await fetchAll(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setRegistering(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!myTeam || !selectedRound) { toast.error("Select a round first"); return; }
    const linkUrls = attachments.filter((a) => a.trim());
    if (!linkUrls.length && pdfFiles.length === 0) {
      toast.error("Add at least one link or PDF");
      return;
    }
    setSubmitting(true);
    try {
      // Upload any selected PDFs first; each returns a public URL that we add
      // to the submission's attachments alongside the link URLs.
      const fileUrls: string[] = [];
      for (const file of pdfFiles) {
        const res = await uploadSubmissionFile(file);
        fileUrls.push(res.url);
      }
      const urls = [...linkUrls, ...fileUrls];
      await uploadSubmission({ team_id: myTeam.id, round_id: selectedRound, attachments: urls });
      toast.success("Submission uploaded!");
      setAttachments([""]);
      setPdfFiles([]);
      setSelectedRound("");
      await fetchAll(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitPreference = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dashboard?.team?.id || !prefName.trim()) { toast.error("Team name required"); return; }
    setSubmittingPref(true);
    try {
      await submitTeamPreference(id, dashboard.team.id, prefName.trim(), prefThemeId || undefined);
      toast.success("Preference submitted!");
      setShowPrefForm(false);
      const prefs = await getTeamPreferences(id, dashboard.team.id).catch(() => [] as TeamPreference[]);
      setPreferences(prefs);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to submit preference");
    } finally {
      setSubmittingPref(false);
    }
  };

  const dismissNotif = async (nid: string) => {
    setDismissedNotifs((prev) => new Set([...prev, nid]));
    await markNotificationRead(nid).catch(() => null);
  };

  // Activity log assembly
  const activityLog: Array<{ date: string; label: string }> = [];
  if (dashboard?.submissions) {
    for (const sub of dashboard.submissions) {
      const round = rounds.find((r) => r.id === sub.round_id);
      if (sub.submitted_at) {
        activityLog.push({ date: sub.submitted_at, label: `Submitted for ${round?.name ?? "a round"}` });
      }
      if (sub.final_score != null) {
        activityLog.push({ date: sub.submitted_at ?? "", label: `Score received: ${sub.final_score}/100 for ${round?.name ?? "a round"}` });
      }
    }
  }
  if (dashboard?.progression_status === "advancing") {
    activityLog.push({ date: "", label: "Advanced to next round" });
  }
  if (dashboard?.progression_status === "eliminated") {
    activityLog.push({ date: "", label: "Eliminated from event" });
  }
  activityLog.sort((a, b) => (b.date > a.date ? 1 : -1));

  const unreadNotifs = (dashboard?.notifications ?? []).filter((n) => !dismissedNotifs.has(n.id));

  const progressStatus = dashboard?.progression_status;
  const progressColor = progressStatus === "advancing" ? "#4ade80" : progressStatus === "eliminated" ? "#f87171" : "#fbbf24";

  const pageWrap: React.CSSProperties = { minHeight: "100vh", background: "#0a0a0a" };
  const container: React.CSSProperties = { maxWidth: "52rem", margin: "0 auto", padding: "5.5rem 1.5rem 3rem" };

  // Derive my preference from the list
  const myPref = preferences.find((p) => p.participant_id === myParticipantId);
  const allSubmitted = dashboard?.team?.member_count != null && preferences.length >= dashboard.team.member_count;
  const voteCounts: Record<string, { name: string; themeId: string | null; count: number }> = {};
  preferences.forEach((p) => {
    const key = `${p.preferred_name}|||${p.preferred_theme_id}`;
    if (!voteCounts[key]) voteCounts[key] = { name: p.preferred_name, themeId: p.preferred_theme_id, count: 0 };
    voteCounts[key].count++;
  });
  const topVote = Object.values(voteCounts).sort((a, b) => b.count - a.count)[0];
  const hasMajority = topVote && allSubmitted && topVote.count > (dashboard?.team?.member_count ?? 0) / 2;
  const hasTie = allSubmitted && !hasMajority;

  const showThemesSection = registered && dashboard?.team && ["registration", "team_formation", "submission"].includes(event?.stage ?? "");

  if (authLoading || loading) {
    return (
      <div style={pageWrap}>
        <Navbar />
        <div style={container}>
          <div className="shimmer" style={{ height: "2rem", width: "14rem", borderRadius: "0.5rem", marginBottom: "1rem" }} />
          <div className="shimmer" style={{ height: "12rem", borderRadius: "0.75rem" }} />
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div style={pageWrap}>
        <Navbar />
        <div style={{ ...container, display: "flex", alignItems: "center", justifyContent: "center", height: "80vh" }}>
          <p style={{ color: "rgba(255,255,255,0.5)" }}>Please log in to view this event.</p>
        </div>
      </div>
    );
  }

  if (!event) {
    return (
      <div style={pageWrap}>
        <Navbar />
        <div style={{ ...container, display: "flex", alignItems: "center", justifyContent: "center", height: "80vh" }}>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>Event not found</p>
        </div>
      </div>
    );
  }

  return (
    <div style={pageWrap}>
      <Navbar />
      <div style={container}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

          {/* Event header */}
          <div style={card}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.75rem" }}>
              <EventStatusBadge status={event.status} />
              <EventStageBadge stage={event.stage} />
            </div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 900, fontStyle: "italic", color: "#fff", margin: 0 }}>
              {event.name}
            </h1>
            <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "#e8503a", fontWeight: 500 }}>{event.type}</p>
            <p style={{ marginTop: "0.75rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.5)", lineHeight: 1.6 }}>{event.description}</p>
            <div style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid #222", fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>
              {registeredCount} participant{registeredCount !== 1 ? "s" : ""} registered
            </div>
          </div>

          {/* Stage pipeline */}
          <div style={card}>
            <h2 style={{ fontSize: "0.875rem", fontWeight: 700, color: "rgba(255,255,255,0.5)", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 1.25rem" }}>
              Event Progress
            </h2>
            <DynamicPipeline eventId={id} />
          </div>

          {/* Your bracket matches (renders only if the event has a bracket) */}
          <MyMatchesCard eventId={id} />

          {/* Your team */}
          {dashboard?.team && (
            <>
              <button
                onClick={() => setTeamModalOpen(true)}
                style={{
                  ...card, display: "flex", alignItems: "center", gap: "0.75rem",
                  width: "100%", cursor: "pointer", textAlign: "left",
                  border: "1px solid rgba(99,102,241,0.25)", background: "rgba(99,102,241,0.08)",
                  transition: "border-color 0.2s",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = "rgba(99,102,241,0.5)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(99,102,241,0.25)"; }}
              >
                <Trophy size={20} color="#6366f1" />
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", margin: 0 }}>
                    Your Team: {dashboard.team.name}
                  </p>
                  <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
                    {dashboard.team.member_count ?? 0} member{(dashboard.team.member_count ?? 0) !== 1 ? "s" : ""} · Click to view
                  </p>
                </div>
                {progressStatus && (
                  <span style={{
                    padding: "0.2rem 0.6rem", borderRadius: "9999px", fontSize: "0.7rem", fontWeight: 700,
                    background: `${progressColor}20`, color: progressColor, textTransform: "capitalize",
                  }}>
                    {progressStatus}
                  </span>
                )}
                <Users size={16} color="rgba(99,102,241,0.6)" />
              </button>
              {myTeam && (
                <TeamDetailModal
                  open={teamModalOpen}
                  onClose={() => setTeamModalOpen(false)}
                  eventId={id}
                  teamId={myTeam.id}
                  teamName={myTeam.name}
                  initialTeam={myTeam}
                />
              )}
            </>
          )}

          {/* Team name & theme consensus */}
          {showThemesSection && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 0.75rem" }}>
                Team Name & Theme
              </h2>
              <div style={{ marginBottom: "0.75rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.5)" }}>
                Current: <span style={{ color: "#fff", fontWeight: 600 }}>{dashboard?.team?.name}</span>
                {dashboard?.team?.theme_id && themes.find((t) => t.id === dashboard?.team?.theme_id) && (
                  <> · Theme: <span style={{ color: "#e8503a", fontWeight: 600 }}>{themes.find((t) => t.id === dashboard?.team?.theme_id)?.name}</span></>
                )}
              </div>

              {hasMajority && (
                <div style={{ padding: "0.75rem", borderRadius: "0.5rem", background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.2)", fontSize: "0.8rem", color: "#4ade80" }}>
                  ✓ Confirmed: "{topVote.name}" · {topVote.count}/{dashboard?.team?.member_count} votes
                </div>
              )}

              {hasTie && (
                <div style={{ padding: "0.75rem", borderRadius: "0.5rem", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", marginBottom: "0.75rem" }}>
                  <p style={{ fontSize: "0.8rem", fontWeight: 600, color: "#f87171", margin: "0 0 0.375rem" }}>⚠ Conflict detected</p>
                  {Object.values(voteCounts).map((v) => (
                    <p key={v.name + v.themeId} style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.5)", margin: "0.2rem 0" }}>
                      "{v.name}" — {v.count} vote{v.count !== 1 ? "s" : ""}
                    </p>
                  ))}
                  <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", marginTop: "0.5rem" }}>Emails sent. Please coordinate and resubmit.</p>
                </div>
              )}

              {!hasMajority && !hasTie && (
                <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)", marginBottom: "0.5rem" }}>
                  {preferences.length}/{dashboard?.team?.member_count ?? "?"} members submitted
                  {myPref && <> · Your vote: "{myPref.preferred_name}"</>}
                </p>
              )}

              {!showPrefForm ? (
                <button
                  onClick={() => { setShowPrefForm(true); setPrefName(dashboard?.team?.name ?? ""); }}
                  style={{
                    marginTop: "0.5rem", fontSize: "0.8rem", color: "#e8503a", background: "transparent",
                    border: "none", cursor: "pointer", padding: 0, textDecoration: "underline",
                  }}
                >
                  {myPref ? "Change my preference" : "Suggest a different name or theme"}
                </button>
              ) : (
                <form onSubmit={handleSubmitPreference} style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <div>
                    <label style={{ display: "block", marginBottom: "0.375rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>Team Name</label>
                    <input value={prefName} onChange={(e) => setPrefName(e.target.value)} style={inputBase} required />
                  </div>
                  {themes.length > 0 && (
                    <div>
                      <label style={{ display: "block", marginBottom: "0.375rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>Theme</label>
                      <select value={prefThemeId} onChange={(e) => setPrefThemeId(e.target.value)} style={inputBase}>
                        <option value="">No theme</option>
                        {themes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </select>
                    </div>
                  )}
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <Button type="submit" variant="primary" loading={submittingPref}>Submit Preference</Button>
                    <Button type="button" variant="secondary" onClick={() => setShowPrefForm(false)}>Cancel</Button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Rounds + submission history */}
          {rounds.length > 0 && registered && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 1rem" }}>
                Rounds & Submissions
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {rounds.map((r) => {
                  const sub = dashboard?.submissions?.find((s) => s.round_id === r.id);
                  const submissionClosed = closedRoundIds.includes(r.id);
                  return (
                    <div key={r.id} style={{
                      padding: "0.875rem 1rem", borderRadius: "0.5rem",
                      background: "rgba(255,255,255,0.03)", border: "1px solid #1e1e1e",
                    }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <div>
                          <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", margin: 0 }}>{r.name}</p>
                          <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
                            {r.status}
                            {r.start_date && ` · ${new Date(r.start_date).toLocaleDateString()}`}
                          </p>
                        </div>
                        <span style={{
                          padding: "0.15rem 0.5rem", borderRadius: "9999px", fontSize: "0.7rem", fontWeight: 600,
                          background: r.status === "active" ? "rgba(34,197,94,0.12)" : r.status === "upcoming" ? "rgba(251,191,36,0.12)" : "rgba(148,163,184,0.12)",
                          color: r.status === "active" ? "#4ade80" : r.status === "upcoming" ? "#fbbf24" : "#94a3b8",
                        }}>
                          {r.status}
                        </span>
                      </div>
                      {sub ? (
                        <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.5)" }}>
                          ✓ Submitted {sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString() : ""}
                          {sub.final_score != null && <> · Score: <span style={{ color: "#4ade80", fontWeight: 700 }}>{sub.final_score}/100</span></>}
                        </div>
                      ) : submissionClosed ? (
                        <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "rgba(248,113,113,0.8)" }}>Submissions closed</div>
                      ) : (
                        <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.35)" }}>No submission yet</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Progression invitation for qualifying teams */}
          {registered && !isEliminated && progressStatus === "advancing" && (
            <div style={{ ...card, border: "1px solid rgba(74,222,128,0.3)", background: "rgba(74,222,128,0.08)" }}>
              <p style={{ fontSize: "0.95rem", fontWeight: 700, color: "#4ade80", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Trophy size={18} color="#4ade80" /> You&apos;re through to the next round!
              </p>
              <p style={{ marginTop: "0.4rem", fontSize: "0.85rem", color: "rgba(255,255,255,0.6)" }}>
                Congratulations — your team qualified. Watch this page and your email for the next round&apos;s
                submission window and deadlines.
              </p>
            </div>
          )}

          {/* Evaluators / judging panel */}
          {registered && (dashboard?.evaluators?.length ?? 0) > 0 && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Award size={18} color="#e8503a" /> Your Evaluators
              </h2>
              <p style={{ margin: "0 0 0.75rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>
                Your submission is reviewed by a panel of judges.
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {dashboard!.evaluators!.map((j) => (
                  <div key={j.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.625rem 0.875rem", borderRadius: "0.5rem", background: "rgba(255,255,255,0.03)", border: "1px solid #1e1e1e" }}>
                    <div style={{ width: "2rem", height: "2rem", borderRadius: "9999px", background: "rgba(232,80,58,0.12)", color: "#e8503a", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: "0.8rem", flexShrink: 0 }}>
                      {j.name?.charAt(0)?.toUpperCase() ?? "J"}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", margin: 0 }}>{j.name}</p>
                      {(j.institution || (j.expertise && j.expertise.length > 0)) && (
                        <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
                          {[j.institution, (j.expertise ?? []).join(", ")].filter(Boolean).join(" · ")}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Key dates & deadlines */}
          {registered && rounds.some((r) => r.start_date || r.end_date) && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Clock size={18} color="#e8503a" /> Key Dates & Deadlines
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {rounds.filter((r) => r.start_date || r.end_date).map((r) => (
                  <div key={r.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem", fontSize: "0.8rem" }}>
                    <span style={{ color: "#fff", fontWeight: 600 }}>{r.name}</span>
                    <span style={{ color: "rgba(255,255,255,0.5)" }}>
                      {r.start_date && new Date(r.start_date).toLocaleDateString("en-US", { day: "numeric", month: "short" })}
                      {r.start_date && r.end_date && " → "}
                      {r.end_date && <span style={{ color: "#fbbf24" }}>{new Date(r.end_date).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}</span>}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Eliminated banner */}
          {registered && isEliminated && (
            <div style={{ ...card, border: "1px solid rgba(248,113,113,0.25)", background: "rgba(248,113,113,0.08)" }}>
              <p style={{ fontSize: "0.95rem", fontWeight: 700, color: "#f87171", margin: 0 }}>
                Your team did not advance
              </p>
              <p style={{ marginTop: "0.4rem", fontSize: "0.85rem", color: "rgba(255,255,255,0.55)" }}>
                Thank you for participating! Submissions for further rounds are closed for your team.
                Your participation certificate will be emailed to you.
              </p>
            </div>
          )}

          {/* Submit project */}
          {registered && !isEliminated && event.stage === "submission" && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 0.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Send size={18} color="#e8503a" /> Submit Project
              </h2>
              <p style={{ marginBottom: "1.25rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.4)" }}>
                Add your project links (GitHub, demo, video) and/or upload PDF documents.
              </p>
              {!dashboard?.team ? (
                <p style={{ fontSize: "0.875rem", color: "rgba(250,204,21,0.7)" }}>
                  You need to be assigned to a team before you can submit.
                </p>
              ) : (
                <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <div>
                    <label style={{ display: "block", marginBottom: "0.375rem", fontSize: "0.875rem", fontWeight: 500, color: "rgba(255,255,255,0.7)" }}>Round *</label>
                    <select value={selectedRound} onChange={(e) => setSelectedRound(e.target.value)} required style={inputBase}>
                      <option value="">Select a round...</option>
                      {rounds.filter((r) => !closedRoundIds.includes(r.id)).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                    {rounds.every((r) => closedRoundIds.includes(r.id)) && rounds.length > 0 && (
                      <p style={{ marginTop: "0.375rem", fontSize: "0.75rem", color: "rgba(250,204,21,0.7)" }}>
                        Submissions are closed for all rounds — the event has moved on.
                      </p>
                    )}
                  </div>

                  {/* Your question paper (quiz rounds only — renders nothing otherwise) */}
                  {selectedRound && <QuizPaperCard roundId={selectedRound} />}
                  <div>
                    <label style={{ display: "block", marginBottom: "0.375rem", fontSize: "0.875rem", fontWeight: 500, color: "rgba(255,255,255,0.7)" }}>Project Links</label>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      {attachments.map((url, i) => (
                        <div key={i} style={{ display: "flex", gap: "0.5rem" }}>
                          <input
                            type="url"
                            value={url}
                            onChange={(e) => setAttachments((prev) => prev.map((a, idx) => idx === i ? e.target.value : a))}
                            placeholder="https://github.com/your-project"
                            style={{ ...inputBase, flex: 1 }}
                          />
                          {attachments.length > 1 && (
                            <button
                              type="button"
                              onClick={() => setAttachments((prev) => prev.filter((_, idx) => idx !== i))}
                              style={{ display: "flex", height: "2.5rem", width: "2.5rem", alignItems: "center", justifyContent: "center", borderRadius: "0.5rem", border: "1px solid #222", background: "transparent", color: "rgba(255,255,255,0.3)", cursor: "pointer" }}
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={() => setAttachments((prev) => [...prev, ""])}
                      style={{ marginTop: "0.5rem", display: "inline-flex", alignItems: "center", gap: "0.375rem", fontSize: "0.75rem", color: "#e8503a", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
                    >
                      <Plus size={14} /> Add another link
                    </button>
                  </div>

                  {/* PDF uploads */}
                  <div>
                    <label style={{ display: "block", marginBottom: "0.375rem", fontSize: "0.875rem", fontWeight: 500, color: "rgba(255,255,255,0.7)" }}>
                      PDF Documents (optional)
                    </label>
                    <p style={{ margin: "0 0 0.5rem", fontSize: "0.75rem", color: "rgba(255,255,255,0.35)" }}>
                      Upload report/slides as PDF. Files are hosted by the organizer and shared with judges.
                    </p>
                    {pdfFiles.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "0.5rem" }}>
                        {pdfFiles.map((file, i) => (
                          <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.5rem 0.75rem", borderRadius: "0.5rem", background: "rgba(255,255,255,0.04)", border: "1px solid #1e1e1e" }}>
                            <FileText size={16} color="#e8503a" />
                            <span style={{ flex: 1, fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB
                            </span>
                            <button
                              type="button"
                              onClick={() => setPdfFiles((prev) => prev.filter((_, idx) => idx !== i))}
                              style={{ display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "0.375rem", border: "none", background: "transparent", color: "rgba(255,255,255,0.3)", cursor: "pointer" }}
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    <label
                      style={{ display: "inline-flex", alignItems: "center", gap: "0.375rem", fontSize: "0.75rem", color: "#e8503a", cursor: "pointer" }}
                    >
                      <Upload size={14} /> Add PDF file
                      <input
                        type="file"
                        accept="application/pdf,.pdf"
                        multiple
                        style={{ display: "none" }}
                        onChange={(e) => {
                          const picked = Array.from(e.target.files ?? []).filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
                          if (picked.length !== (e.target.files?.length ?? 0)) {
                            toast.error("Only PDF files are allowed");
                          }
                          setPdfFiles((prev) => [...prev, ...picked]);
                          e.target.value = "";
                        }}
                      />
                    </label>
                  </div>

                  <Button type="submit" variant="primary" size="lg" fullWidth loading={submitting}>
                    <Send size={16} /> Submit Project
                  </Button>
                </form>
              )}
            </div>
          )}

          {/* Registration form / status */}
          {!registered ? (
            event.stage !== "registration" ? (
              <div style={{ ...card, textAlign: "center" }}>
                <p style={{ color: "rgba(255,255,255,0.4)" }}>Registration is currently closed for this event.</p>
              </div>
            ) : (
              <div style={card}>
                <h2 style={{ margin: "0 0 1.25rem", fontSize: "1.125rem", fontWeight: 700, color: "#fff" }}>
                  Register Now
                </h2>
                <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <Input label="Institution / Company" value={regForm.institution} onChange={(e) => setRegForm((p) => ({ ...p, institution: e.target.value }))} placeholder="Your university or company" fullWidth />
                  <Input label="Skills" value={regForm.skills} onChange={(e) => setRegForm((p) => ({ ...p, skills: e.target.value }))} placeholder="e.g., Python, React, ML" hint="Comma-separated — used for team matching" fullWidth />
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "1rem" }}>
                    <Input label="Gender" value={regForm.gender} onChange={(e) => setRegForm((p) => ({ ...p, gender: e.target.value }))} placeholder="Optional" />
                    <Input label="Age" type="number" value={regForm.age} onChange={(e) => setRegForm((p) => ({ ...p, age: e.target.value }))} placeholder="Optional" />
                  </div>
                  <Input label="Phone" type="tel" value={regForm.phone} onChange={(e) => setRegForm((p) => ({ ...p, phone: e.target.value }))} placeholder="+1 234 567 8900" fullWidth />
                  <Button type="submit" variant="primary" size="lg" fullWidth loading={registering}>
                    Register for {event.name}
                  </Button>
                </form>
              </div>
            )
          ) : (
            event.stage !== "submission" && (
              <div style={{ borderRadius: "0.75rem", border: "1px solid rgba(34,197,94,0.2)", background: "rgba(34,197,94,0.1)", padding: "1.5rem", textAlign: "center" }}>
                <p style={{ fontSize: "1.125rem", fontWeight: 700, color: "#4ade80", margin: 0 }}>You&apos;re registered!</p>
                <p style={{ marginTop: "0.5rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.5)" }}>Check back for team assignments and round updates.</p>
              </div>
            )
          )}

          {/* Leaderboard */}
          {(event.stage === "results" || event.stage === "completed") && leaderboard.length > 0 && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Award size={18} color="#e8503a" /> Leaderboard
              </h2>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #222" }}>
                    {["Rank", "Team", "Score"].map((h) => (
                      <th key={h} style={{ padding: "0.5rem 0.75rem", textAlign: "left", color: "rgba(255,255,255,0.4)", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.slice(0, 10).map((sub, i) => {
                    const team = teams.find((t) => t.id === sub.team_id);
                    const isMyTeam = dashboard?.team?.id === sub.team_id;
                    return (
                      <tr key={sub.id} style={{ borderBottom: "1px solid #1a1a1a", background: isMyTeam ? "rgba(99,102,241,0.06)" : "transparent" }}>
                        <td style={{ padding: "0.625rem 0.75rem", fontWeight: 700, color: i < 3 ? "#e8503a" : "#fff" }}>#{i + 1}</td>
                        <td style={{ padding: "0.625rem 0.75rem", color: "#fff", fontWeight: isMyTeam ? 700 : 400 }}>
                          {team?.name ?? sub.team_id.slice(0, 8)}
                          {isMyTeam && <span style={{ marginLeft: "0.375rem", fontSize: "0.65rem", color: "#6366f1" }}>(You)</span>}
                        </td>
                        <td style={{ padding: "0.625rem 0.75rem", color: "#fff", fontWeight: 700 }}>{sub.final_score ?? "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Activity log */}
          {activityLog.length > 0 && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 1rem" }}>Activity Log</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
                {activityLog.map((entry, i) => (
                  <div key={i} style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                    <div style={{ flexShrink: 0, marginTop: "0.25rem", width: "8px", height: "8px", borderRadius: "9999px", background: "#e8503a" }} />
                    <div>
                      <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.75)", margin: 0 }}>{entry.label}</p>
                      {entry.date && <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>{new Date(entry.date).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notifications */}
          {unreadNotifs.length > 0 && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Bell size={16} color="#e8503a" /> Notifications
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {unreadNotifs.map((n) => (
                  <div key={n.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.75rem 1rem", borderRadius: "0.5rem", background: "rgba(232,80,58,0.08)", border: "1px solid rgba(232,80,58,0.15)" }}>
                    <Clock size={14} color="#e8503a" />
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", margin: 0 }}>{n.title}</p>
                      <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", margin: 0 }}>{n.message}</p>
                    </div>
                    <button onClick={() => dismissNotif(n.id)} style={{ background: "transparent", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: "0.75rem" }}>Dismiss</button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
