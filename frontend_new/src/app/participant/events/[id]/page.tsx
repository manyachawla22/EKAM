"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Users, Trophy, Calendar, Send, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import {
  getEvent,
  registerParticipant,
  listRounds,
  listTeams,
  uploadSubmission,
  listParticipants,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event, Round, Team } from "@/types";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { EventStatusBadge, EventStageBadge } from "@/components/ui/Badge";
import Navbar from "@/components/layout/Navbar";
import TeamDetailModal from "@/components/ui/TeamDetailModal";

const cardStyle: React.CSSProperties = {
  borderRadius: "0.75rem",
  border: "1px solid #222",
  background: "#111",
  padding: "1.5rem",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  marginBottom: "0.375rem",
  fontSize: "0.875rem",
  fontWeight: 500,
  color: "rgba(255,255,255,0.7)",
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

export default function ParticipantEventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { profile } = useAuth();
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [registered, setRegistered] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [myTeam, setMyTeam] = useState<Team | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [teamModalOpen, setTeamModalOpen] = useState(false);
  const [selectedRound, setSelectedRound] = useState<string>("");
  const [attachments, setAttachments] = useState<string[]>([""]);

  const [form, setForm] = useState({
    institution: "",
    skills: "",
    gender: "",
    age: "",
    phone: "",
  });

  const fetchAll = useCallback(
    async (isInitial = false) => {
      if (!id) return;
      if (isInitial) setLoading(true);
      try {
        const [ev, roundsData, teams, participants] = await Promise.all([
          getEvent(id),
          listRounds(id).catch((err) => {
            console.warn("[participant page] listRounds failed:", err);
            return [];
          }),
          listTeams(id).catch((err) => {
            console.warn("[participant page] listTeams failed:", err);
            return [];
          }),
          profile
            ? listParticipants(id).catch((err) => {
                console.warn(
                  "[participant page] listParticipants failed:",
                  err
                );
                return [];
              })
            : Promise.resolve([]),
        ]);
        setEvent(ev);
        setRounds(roundsData);
        if (profile) {
          const meEmail = (profile.email || "").trim().toLowerCase();
          const myParticipant = participants.find(
            (p) => (p.email || "").trim().toLowerCase() === meEmail
          );
          if (myParticipant) {
            setRegistered(true);
            const team = teams.find((t) =>
              t.members?.some(
                (m) => m.participant_id === myParticipant.id
              )
            );
            if (team) setMyTeam(team);
            else setMyTeam(null);
          } else {
            setRegistered(false);
            setMyTeam(null);
          }
        }
      } catch (err) {
        if (isInitial)
          toast.error(
            err instanceof Error ? err.message : "Failed to load event"
          );
      } finally {
        if (isInitial) setLoading(false);
      }
    },
    [id, profile]
  );

  useEffect(() => {
    fetchAll(true);
  }, [fetchAll]);

  // Re-pull when the tab regains focus so an organizer-side change (event
  // stage flip, team assignment, etc.) shows up without a hard refresh.
  useEffect(() => {
    const onFocus = () => fetchAll(false);
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [fetchAll]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) {
      toast.error("Please log in first");
      return;
    }
    setRegistering(true);
    try {
      const registered = await registerParticipant({
        name: profile.name || profile.email,
        email: profile.email,
        event_id: id,
        institution: form.institution || undefined,
        skills: form.skills
          ? form.skills.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        gender: form.gender || undefined,
        age: form.age ? parseInt(form.age) : undefined,
        phone: form.phone || undefined,
      });
      setRegistered(true);
      // Re-fetch teams so we pick up any pre-existing team membership the
      // organizer may have set before this participant clicked Register.
      try {
        const teams = await listTeams(id);
        const team = teams.find((t) =>
          t.members?.some((m) => m.participant_id === registered.id)
        );
        if (team) setMyTeam(team);
      } catch {
        // non-fatal; team status will sync on next page load
      }
      toast.success("Registered successfully!");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Registration failed"
      );
    } finally {
      setRegistering(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!myTeam) {
      toast.error("You must be in a team to submit");
      return;
    }
    if (!selectedRound) {
      toast.error("Please select a round");
      return;
    }
    const urls = attachments.filter((a) => a.trim());
    if (urls.length === 0) {
      toast.error("Please add at least one attachment URL");
      return;
    }
    setSubmitting(true);
    try {
      await uploadSubmission({
        team_id: myTeam.id,
        round_id: selectedRound,
        attachments: urls,
      });
      toast.success("Submission uploaded!");
      setAttachments([""]);
      setSelectedRound("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const addAttachment = () => setAttachments((prev) => [...prev, ""]);
  const removeAttachment = (i: number) =>
    setAttachments((prev) => prev.filter((_, idx) => idx !== i));
  const updateAttachment = (i: number, val: string) =>
    setAttachments((prev) => prev.map((a, idx) => (idx === i ? val : a)));

  const pageWrap: React.CSSProperties = {
    minHeight: "100vh",
    background: "#0a0a0a",
  };
  const container: React.CSSProperties = {
    maxWidth: "48rem",
    margin: "0 auto",
    padding: "6rem 1.5rem 3rem",
  };

  if (loading) {
    return (
      <div style={pageWrap}>
        <Navbar />
        <div style={container}>
          <div
            className="shimmer"
            style={{ height: "2rem", width: "12rem", borderRadius: "0.5rem", marginBottom: "1rem" }}
          />
          <div
            className="shimmer"
            style={{ height: "10rem", borderRadius: "0.75rem" }}
          />
        </div>
      </div>
    );
  }

  if (!event) {
    return (
      <div style={pageWrap}>
        <Navbar />
        <div
          style={{
            display: "flex",
            height: "100vh",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <p style={{ color: "rgba(255,255,255,0.4)" }}>Event not found</p>
        </div>
      </div>
    );
  }

  return (
    <div style={pageWrap}>
      <Navbar />
      <div style={container}>
        <Link
          href="/participant/events"
          style={{
            marginBottom: "1.5rem",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.875rem",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          <ArrowLeft size={16} />
          Browse events
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "1.5rem",
            marginTop: "0.5rem",
          }}
        >
          {/* Event info */}
          <div style={cardStyle}>
            <div
              style={{
                marginBottom: "1rem",
                display: "flex",
                flexWrap: "wrap",
                gap: "0.5rem",
              }}
            >
              <EventStatusBadge status={event.status} />
              <EventStageBadge stage={event.stage} />
            </div>
            <h1
              style={{
                fontSize: "1.5rem",
                fontWeight: 900,
                fontStyle: "italic",
                color: "#fff",
                margin: 0,
              }}
            >
              {event.name}
            </h1>
            <p
              style={{
                marginTop: "0.25rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "#e8503a",
              }}
            >
              {event.type}
            </p>
            <p
              style={{
                marginTop: "1rem",
                fontSize: "0.875rem",
                color: "rgba(255,255,255,0.5)",
                lineHeight: 1.6,
              }}
            >
              {event.description}
            </p>
            <div
              style={{
                marginTop: "1.25rem",
                display: "flex",
                flexWrap: "wrap",
                gap: "1.25rem",
                borderTop: "1px solid #222",
                paddingTop: "1.25rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.5)",
                }}
              >
                <Users size={16} />
                Max {event.max_participants} participants
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.5)",
                }}
              >
                <Trophy size={16} />
                Stage: {event.stage.replace("_", " ")}
              </div>
              {event.created_at && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    fontSize: "0.875rem",
                    color: "rgba(255,255,255,0.5)",
                  }}
                >
                  <Calendar size={16} />
                  {new Date(event.created_at).toLocaleDateString()}
                </div>
              )}
            </div>
          </div>

          {/* Team badge */}
          {myTeam && (
            <>
              <button
                onClick={() => setTeamModalOpen(true)}
                style={{
                  borderRadius: "0.75rem",
                  border: "1px solid rgba(99,102,241,0.25)",
                  background: "rgba(99,102,241,0.1)",
                  padding: "1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  width: "100%",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "border-color 0.2s, background 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(99,102,241,0.5)";
                  e.currentTarget.style.background = "rgba(99,102,241,0.15)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(99,102,241,0.25)";
                  e.currentTarget.style.background = "rgba(99,102,241,0.1)";
                }}
              >
                <Trophy size={20} color="#6366f1" />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", margin: 0 }}>
                    Your Team: {myTeam.name}
                  </p>
                  <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
                    {myTeam.members?.length || 0} member{(myTeam.members?.length || 0) !== 1 ? "s" : ""} · Click to view
                  </p>
                </div>
                <Users size={16} color="rgba(99,102,241,0.6)" />
              </button>
              <TeamDetailModal
                open={teamModalOpen}
                onClose={() => setTeamModalOpen(false)}
                eventId={id}
                teamId={myTeam.id}
                teamName={myTeam.name}
                initialTeam={myTeam}
              />
            </>
          )}

          {/* Submit section */}
          {registered && event.stage === "submission" && (
            <div style={cardStyle}>
              <h2
                style={{
                  margin: "0 0 0.25rem",
                  fontSize: "1.125rem",
                  fontWeight: 700,
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <Send size={20} color="#e8503a" />
                Submit Project
              </h2>
              <p
                style={{
                  marginBottom: "1.25rem",
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.4)",
                }}
              >
                Add your project links (GitHub, demo, video, etc.)
              </p>
              {!myTeam ? (
                <p
                  style={{
                    fontSize: "0.875rem",
                    color: "rgba(250,204,21,0.7)",
                  }}
                >
                  You need to be assigned to a team before you can submit.
                </p>
              ) : (
                <form
                  onSubmit={handleSubmit}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "1rem",
                  }}
                >
                  <div>
                    <label style={labelStyle}>Round *</label>
                    <select
                      value={selectedRound}
                      onChange={(e) => setSelectedRound(e.target.value)}
                      required
                      style={inputBase}
                    >
                      <option value="">Select a round...</option>
                      {rounds.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={labelStyle}>Attachment URLs *</label>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.5rem",
                      }}
                    >
                      {attachments.map((url, i) => (
                        <div
                          key={i}
                          style={{ display: "flex", gap: "0.5rem" }}
                        >
                          <input
                            type="url"
                            value={url}
                            onChange={(e) =>
                              updateAttachment(i, e.target.value)
                            }
                            placeholder="https://github.com/your-project"
                            style={{ ...inputBase, flex: 1 }}
                          />
                          {attachments.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeAttachment(i)}
                              style={{
                                display: "flex",
                                height: "2.5rem",
                                width: "2.5rem",
                                alignItems: "center",
                                justifyContent: "center",
                                borderRadius: "0.5rem",
                                border: "1px solid #222",
                                background: "transparent",
                                color: "rgba(255,255,255,0.3)",
                                cursor: "pointer",
                              }}
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={addAttachment}
                      style={{
                        marginTop: "0.5rem",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.375rem",
                        fontSize: "0.75rem",
                        color: "#e8503a",
                        background: "transparent",
                        border: "none",
                        cursor: "pointer",
                        padding: 0,
                      }}
                    >
                      <Plus size={14} />
                      Add another link
                    </button>
                  </div>

                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    fullWidth
                    loading={submitting}
                  >
                    <Send size={16} />
                    Submit Project
                  </Button>
                </form>
              )}
            </div>
          )}

          {/* Registration */}
          {registered ? (
            event.stage === "submission" ? null : (
              <div
                style={{
                  borderRadius: "0.75rem",
                  border: "1px solid rgba(34,197,94,0.2)",
                  background: "rgba(34,197,94,0.1)",
                  padding: "1.5rem",
                  textAlign: "center",
                }}
              >
                <p
                  style={{
                    fontSize: "1.125rem",
                    fontWeight: 700,
                    color: "#4ade80",
                    margin: 0,
                  }}
                >
                  You&apos;re registered!
                </p>
                <p
                  style={{
                    marginTop: "0.5rem",
                    fontSize: "0.875rem",
                    color: "rgba(255,255,255,0.5)",
                  }}
                >
                  Check back for team assignments and round updates.
                </p>
              </div>
            )
          ) : event.stage !== "registration" ? (
            <div style={{ ...cardStyle, textAlign: "center" }}>
              <p style={{ color: "rgba(255,255,255,0.4)" }}>
                Registration is currently closed for this event.
              </p>
            </div>
          ) : (
            <div style={cardStyle}>
              <h2
                style={{
                  margin: "0 0 1.25rem",
                  fontSize: "1.125rem",
                  fontWeight: 700,
                  color: "#fff",
                }}
              >
                Register Now
              </h2>
              <form
                onSubmit={handleRegister}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "1rem",
                }}
              >
                <Input
                  label="Institution / Company"
                  value={form.institution}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, institution: e.target.value }))
                  }
                  placeholder="Your university or company"
                  fullWidth
                />
                <Input
                  label="Skills"
                  value={form.skills}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, skills: e.target.value }))
                  }
                  placeholder="e.g., Python, React, Machine Learning"
                  hint="Comma-separated — used for team matching"
                  fullWidth
                />
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "1rem",
                  }}
                >
                  <Input
                    label="Gender"
                    value={form.gender}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, gender: e.target.value }))
                    }
                    placeholder="Optional"
                  />
                  <Input
                    label="Age"
                    type="number"
                    value={form.age}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, age: e.target.value }))
                    }
                    placeholder="Optional"
                  />
                </div>
                <Input
                  label="Phone"
                  type="tel"
                  value={form.phone}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, phone: e.target.value }))
                  }
                  placeholder="+1 234 567 8900"
                  fullWidth
                />
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  fullWidth
                  loading={registering}
                >
                  Register for {event.name}
                </Button>
              </form>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
