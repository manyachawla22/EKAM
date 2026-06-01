"use client";

export const dynamic = "force-dynamic";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { createEvent, generateHash } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import Button from "@/components/ui/Button";
import Input, { Textarea, Select } from "@/components/ui/Input";

export default function CreateEventPage() {
  const router = useRouter();
  const { profile } = useAuth();
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    name: "",
    type: "",
    description: "",
    max_participants: 100,
    min_team_size: 1,
    max_team_size: 4,
    team_formation_type: "platform_generated" as
      | "platform_generated"
      | "preformed",
  });

  const handleChange = (
    field: string,
    value: string | number
  ) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) {
      toast.error("You must be logged in to create events");
      return;
    }
    if (!form.name || !form.type || !form.description) {
      toast.error("Please fill in all required fields");
      return;
    }
    if (form.min_team_size > form.max_team_size) {
      toast.error("Min team size cannot exceed max team size");
      return;
    }

    setLoading(true);
    try {
      const event = await createEvent({
        name: form.name,
        type: form.type,
        description: form.description,
        max_participants: form.max_participants,
        min_team_size: form.min_team_size,
        max_team_size: form.max_team_size,
        team_formation_type: form.team_formation_type,
        hash: generateHash(),
        // organizer_id is required by the new backend EventCreate schema.
        organizer_id: profile.id,
      });
      toast.success("Event created successfully!");
      router.push(`/organizer/events/${event.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create event");
    } finally {
      setLoading(false);
    }
  };

  const card: React.CSSProperties = {
    borderRadius: "0.75rem",
    border: "1px solid #222",
    background: "#111",
    padding: "1.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  };
  const sectionTitle: React.CSSProperties = {
    fontSize: "0.875rem",
    fontWeight: 600,
    color: "rgba(255,255,255,0.6)",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    margin: 0,
  };

  return (
    <div style={{ maxWidth: "42rem", margin: "0 auto", width: "100%" }}>
      <button
        onClick={() => router.back()}
        style={{
          marginBottom: "1.5rem",
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
        Back to events
      </button>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1
          style={{
            margin: "0 0 0.25rem",
            fontSize: "1.875rem",
            fontWeight: 900,
            fontStyle: "italic",
            color: "#fff",
          }}
        >
          Create Event
        </h1>
        <p
          style={{
            marginBottom: "2rem",
            fontSize: "0.875rem",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          Set up a new hackathon, coding contest, or team challenge.
        </p>

        <form
          onSubmit={handleSubmit}
          style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}
        >
          <div style={card}>
            <h2 style={sectionTitle}>Basic Info</h2>

            <Input
              label="Event Name *"
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder="e.g., HackFest 2025"
              fullWidth
              required
            />

            <Input
              label="Event Type *"
              value={form.type}
              onChange={(e) => handleChange("type", e.target.value)}
              placeholder="e.g., Hackathon, Coding Contest, Team Challenge"
              fullWidth
              required
            />

            <Textarea
              label="Description *"
              value={form.description}
              onChange={(e) => handleChange("description", e.target.value)}
              placeholder="Describe what the event is about, its goals, and what participants can expect..."
              fullWidth
              required
            />

            <Input
              label="Max Participants"
              type="number"
              value={form.max_participants}
              onChange={(e) =>
                handleChange(
                  "max_participants",
                  parseInt(e.target.value) || 100
                )
              }
              min={1}
              max={10000}
              fullWidth
              hint="Maximum number of participants allowed to register"
            />
          </div>

          <div style={card}>
            <h2 style={sectionTitle}>Teams</h2>

            <Select
              label="Team Formation"
              value={form.team_formation_type}
              onChange={(e) =>
                handleChange("team_formation_type", e.target.value)
              }
              fullWidth
              options={[
                {
                  value: "platform_generated",
                  label: "Platform-generated — auto-match participants into teams",
                },
                {
                  value: "preformed",
                  label: "Preformed — participants bring their own teams",
                },
              ]}
            />

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: "1rem",
              }}
            >
              <Input
                label="Min Team Size"
                type="number"
                value={form.min_team_size}
                onChange={(e) =>
                  handleChange(
                    "min_team_size",
                    parseInt(e.target.value) || 1
                  )
                }
                min={1}
                max={20}
                fullWidth
              />
              <Input
                label="Max Team Size"
                type="number"
                value={form.max_team_size}
                onChange={(e) =>
                  handleChange(
                    "max_team_size",
                    parseInt(e.target.value) || 4
                  )
                }
                min={1}
                max={20}
                fullWidth
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.75rem" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.back()}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={loading}
              style={{ flex: 1 }}
            >
              Create Event
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
