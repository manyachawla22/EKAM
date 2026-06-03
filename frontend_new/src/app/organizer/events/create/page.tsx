"use client";

export const dynamic = "force-dynamic";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { createEvent, createTheme, generateHash } from "@/lib/api";
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

  // Themes participants can later pick from (created after the event itself).
  // `skills` is a comma-separated string; split into required_skills on submit.
  const [themes, setThemes] = useState<{ name: string; description: string; skills: string }[]>([]);

  const addTheme = () =>
    setThemes((prev) => [...prev, { name: "", description: "", skills: "" }]);
  const updateTheme = (i: number, field: "name" | "description" | "skills", value: string) =>
    setThemes((prev) => prev.map((t, idx) => (idx === i ? { ...t, [field]: value } : t)));
  const removeTheme = (i: number) =>
    setThemes((prev) => prev.filter((_, idx) => idx !== i));

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

      // Create any themes the organizer added — participants pick from these.
      const validThemes = themes.filter((t) => t.name.trim());
      if (validThemes.length > 0) {
        const results = await Promise.allSettled(
          validThemes.map((t) =>
            createTheme(event.id, {
              name: t.name.trim(),
              description: t.description.trim() || undefined,
              required_skills: (() => {
                const skills = t.skills
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean);
                return skills.length ? skills : undefined;
              })(),
            })
          )
        );
        const failed = results.filter((r) => r.status === "rejected").length;
        if (failed > 0) {
          toast.warning(`Event created, but ${failed} theme(s) could not be saved.`);
        }
      }

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

          <div style={card}>
            <h2 style={sectionTitle}>Themes / Tracks</h2>
            <p
              style={{
                margin: "-0.5rem 0 0",
                fontSize: "0.8rem",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              Optional. Add the themes participants can choose from (e.g. AI/ML,
              Web3, Climate Tech). You can also add these later from the event page.
            </p>

            {themes.map((t, i) => (
              <div
                key={i}
                style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}
              >
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <Input
                    value={t.name}
                    onChange={(e) => updateTheme(i, "name", e.target.value)}
                    placeholder="Theme name — e.g., AI/ML"
                    fullWidth
                  />
                  <Input
                    value={t.description}
                    onChange={(e) => updateTheme(i, "description", e.target.value)}
                    placeholder="Short description (optional)"
                    fullWidth
                  />
                  <Input
                    value={t.skills}
                    onChange={(e) => updateTheme(i, "skills", e.target.value)}
                    placeholder="Required skills — comma separated (e.g. React, ML)"
                    fullWidth
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeTheme(i)}
                  title="Remove theme"
                  style={{
                    display: "flex",
                    height: "2.5rem",
                    width: "2.5rem",
                    flexShrink: 0,
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
              </div>
            ))}

            <button
              type="button"
              onClick={addTheme}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.375rem",
                alignSelf: "flex-start",
                fontSize: "0.8rem",
                color: "#e8503a",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: 0,
              }}
            >
              <Plus size={14} /> Add theme
            </button>
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
