"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Users,
  Layers,
  Send,
  UserCheck,
  BarChart2,
  Edit2,
  ArrowLeft,
  Trophy,
  Trash2,
  Save,
} from "lucide-react";
import { toast } from "sonner";
import {
  getEvent,
  listParticipants,
  listTeams,
  listSubmissions,
  updateEvent,
  deleteEvent,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event, EventStatus, EventStage } from "@/types";
import { EventStatusBadge, EventStageBadge } from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

const STATUSES: EventStatus[] = ["draft", "active", "completed", "archived"];
const STAGES: EventStage[] = [
  "registration",
  "team_formation",
  "submission",
  "evaluation",
  "completed",
];

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
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    participants: 0,
    teams: 0,
    submissions: 0,
  });

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "",
    type: "",
    description: "",
    status: "draft" as EventStatus,
    stage: "registration" as EventStage,
    max_participants: 100,
  });

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    if (!id) return;
    Promise.all([
      getEvent(id),
      listParticipants(id).catch(() => []),
      listTeams(id).catch(() => []),
      // Submissions are scoped by round, not event — leaving as 0 for now.
      Promise.resolve([] as unknown[]),
    ])
      .then(([ev, participants, teams, submissions]) => {
        setEvent(ev);
        setStats({
          participants: (participants as unknown[]).length,
          teams: (teams as unknown[]).length,
          submissions: (submissions as unknown[]).length,
        });
        setEditForm({
          name: ev.name,
          type: ev.type,
          description: ev.description,
          status: ev.status,
          stage: ev.stage,
          max_participants: ev.max_participants,
        });
      })
      .catch((err: Error) =>
        toast.error(err.message || "Failed to load event")
      )
      .finally(() => setLoading(false));
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

  if (loading) {
    return (
      <div
        style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
      >
        <div
          className="shimmer"
          style={{ height: "2rem", width: "12rem", borderRadius: "0.5rem" }}
        />
        <div
          className="shimmer"
          style={{ height: "10rem", borderRadius: "0.75rem" }}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
            gap: "1rem",
          }}
        >
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "6rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (!event) {
    return (
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
        <p style={{ color: "rgba(255,255,255,0.4)" }}>Event not found</p>
        <button
          onClick={() => router.back()}
          style={{
            fontSize: "0.875rem",
            color: "#e8503a",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            textDecoration: "underline",
          }}
        >
          Go back
        </button>
      </div>
    );
  }

  const statCards = [
    {
      label: "Participants",
      value: stats.participants,
      icon: <Users size={20} />,
      color: "#6366f1",
      href: `/organizer/events/${id}/participants`,
    },
    {
      label: "Teams",
      value: stats.teams,
      icon: <Trophy size={20} />,
      color: "#f59e0b",
      href: `/organizer/events/${id}/teams`,
    },
    {
      label: "Submissions",
      value: stats.submissions,
      icon: <Send size={20} />,
      color: "#22c55e",
      href: `/organizer/events/${id}/submissions`,
    },
  ];

  const quickActions = [
    { label: "Rounds", icon: <Layers size={20} />, href: `/organizer/events/${id}/rounds` },
    { label: "Participants", icon: <Users size={20} />, href: `/organizer/events/${id}/participants` },
    { label: "Teams", icon: <Trophy size={20} />, href: `/organizer/events/${id}/teams` },
    { label: "Judges", icon: <UserCheck size={20} />, href: `/organizer/events/${id}/judges` },
    { label: "Submissions", icon: <Send size={20} />, href: `/organizer/events/${id}/submissions` },
    { label: "Reports", icon: <BarChart2 size={20} />, href: `/organizer/events/${id}/reports` },
  ];

  const stageIdx = STAGES.indexOf(event.stage);

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <button
        onClick={() => router.push("/organizer/events")}
        style={{
          marginBottom: "1.25rem",
          display: "inline-flex",
          alignItems: "center",
          gap: "0.5rem",
          fontSize: "0.875rem",
          color: "rgba(255,255,255,0.4)",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          padding: 0,
        }}
      >
        <ArrowLeft size={16} />
        All events
      </button>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}
      >
        {/* Event header */}
        <div style={card}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: "1rem",
              flexWrap: "wrap",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  marginBottom: "0.75rem",
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <EventStatusBadge status={event.status} />
                <EventStageBadge stage={event.stage} />
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.3)",
                  }}
                >
                  #{event.hash?.slice(0, 8)}
                </span>
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
                  marginTop: "0.75rem",
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.5)",
                  lineHeight: 1.6,
                }}
              >
                {event.description}
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
              <button
                onClick={() => setEditOpen(true)}
                title="Edit event"
                style={{
                  display: "flex",
                  height: "2.25rem",
                  width: "2.25rem",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "0.5rem",
                  border: "1px solid #222",
                  background: "transparent",
                  color: "rgba(255,255,255,0.4)",
                  cursor: "pointer",
                }}
              >
                <Edit2 size={16} />
              </button>
              <button
                onClick={() => setDeleteOpen(true)}
                title="Delete event"
                style={{
                  display: "flex",
                  height: "2.25rem",
                  width: "2.25rem",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "0.5rem",
                  border: "1px solid #222",
                  background: "transparent",
                  color: "rgba(255,255,255,0.4)",
                  cursor: "pointer",
                }}
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>

          {/* Stage progress */}
          <div style={{ marginTop: "1.5rem" }}>
            <p
              style={{
                marginBottom: "0.75rem",
                fontSize: "0.75rem",
                color: "rgba(255,255,255,0.3)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Stage Progress
            </p>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              {STAGES.map((stage, i) => {
                const isActive = i === stageIdx;
                const isPast = i < stageIdx;
                return (
                  <div
                    key={stage}
                    style={{
                      flex: 1,
                      display: "flex",
                      alignItems: "center",
                      gap: "0.5rem",
                    }}
                  >
                    <div
                      style={{
                        height: "0.375rem",
                        flex: 1,
                        borderRadius: "9999px",
                        background: isPast
                          ? "#e8503a"
                          : isActive
                          ? "rgba(232,80,58,0.6)"
                          : "#222",
                        transition: "all 0.2s",
                      }}
                    />
                  </div>
                );
              })}
            </div>
            <div
              style={{
                marginTop: "0.375rem",
                display: "flex",
                justifyContent: "space-between",
                fontSize: "0.625rem",
                color: "rgba(255,255,255,0.2)",
              }}
            >
              {STAGES.map((s) => (
                <span key={s}>{s.replace("_", " ")}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Stat cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: "1rem",
          }}
        >
          {statCards.map((stat) => (
            <Link key={stat.label} href={stat.href}>
              <motion.div
                whileHover={{ y: -2 }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  borderRadius: "0.75rem",
                  border: "1px solid #222",
                  background: "#111",
                  padding: "1.25rem",
                  cursor: "pointer",
                  transition: "border-color 0.2s",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    height: "2.75rem",
                    width: "2.75rem",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "0.75rem",
                    background: `${stat.color}20`,
                    color: stat.color,
                  }}
                >
                  {stat.icon}
                </div>
                <div>
                  <p
                    style={{
                      fontSize: "1.5rem",
                      fontWeight: 700,
                      color: "#fff",
                      margin: 0,
                    }}
                  >
                    {stat.value}
                  </p>
                  <p
                    style={{
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.4)",
                      margin: 0,
                    }}
                  >
                    {stat.label}
                  </p>
                </div>
              </motion.div>
            </Link>
          ))}
        </div>

        {/* Quick actions */}
        <div>
          <h2
            style={{
              marginBottom: "1rem",
              fontSize: "0.875rem",
              fontWeight: 600,
              color: "rgba(255,255,255,0.5)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Quick Actions
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: "0.75rem",
            }}
          >
            {quickActions.map((action) => (
              <Link key={action.label} href={action.href}>
                <motion.div
                  whileHover={{ y: -2 }}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "0.5rem",
                    borderRadius: "0.75rem",
                    border: "1px solid #222",
                    background: "#111",
                    padding: "1rem",
                    cursor: "pointer",
                    textAlign: "center",
                    transition: "all 0.2s",
                  }}
                >
                  <span style={{ color: "#e8503a", display: "flex" }}>
                    {action.icon}
                  </span>
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 500,
                      color: "rgba(255,255,255,0.7)",
                    }}
                  >
                    {action.label}
                  </span>
                </motion.div>
              </Link>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Edit modal */}
      <Modal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Edit Event"
        size="lg"
      >
        <form
          onSubmit={handleSave}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <Input
            label="Event Name *"
            value={editForm.name}
            onChange={(e) =>
              setEditForm((p) => ({ ...p, name: e.target.value }))
            }
            fullWidth
            required
          />
          <Input
            label="Type"
            value={editForm.type}
            onChange={(e) =>
              setEditForm((p) => ({ ...p, type: e.target.value }))
            }
            fullWidth
          />
          <div>
            <label style={formLabel}>Description</label>
            <textarea
              value={editForm.description}
              onChange={(e) =>
                setEditForm((p) => ({ ...p, description: e.target.value }))
              }
              rows={3}
              style={{ ...inputBase, resize: "vertical", minHeight: "5rem" }}
            />
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: "1rem",
            }}
          >
            <div>
              <label style={formLabel}>Status</label>
              <select
                value={editForm.status}
                onChange={(e) =>
                  setEditForm((p) => ({
                    ...p,
                    status: e.target.value as EventStatus,
                  }))
                }
                style={inputBase}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={formLabel}>Stage</label>
              <select
                value={editForm.stage}
                onChange={(e) =>
                  setEditForm((p) => ({
                    ...p,
                    stage: e.target.value as EventStage,
                  }))
                }
                style={inputBase}
              >
                {STAGES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <Input
            label="Max Participants"
            type="number"
            value={String(editForm.max_participants)}
            onChange={(e) =>
              setEditForm((p) => ({
                ...p,
                max_participants: parseInt(e.target.value) || 0,
              }))
            }
            fullWidth
          />
          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setEditOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={saving}
              style={{ flex: 1 }}
            >
              <Save size={16} /> Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete confirmation modal */}
      <Modal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Delete Event"
        size="sm"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.6)",
              margin: 0,
            }}
          >
            Are you sure you want to delete{" "}
            <span style={{ fontWeight: 600, color: "#fff" }}>{event.name}</span>?
            This action cannot be undone.
          </p>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <Button
              variant="secondary"
              onClick={() => setDeleteOpen(false)}
              style={{ flex: 1 }}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={deleting}
              onClick={handleDelete}
              style={{ flex: 1 }}
            >
              <Trash2 size={16} /> Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
