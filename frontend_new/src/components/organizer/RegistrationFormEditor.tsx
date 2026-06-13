"use client";

import { useState } from "react";
import { ClipboardList, Plus, Trash2, Send } from "lucide-react";
import { toast } from "sonner";
import Button from "@/components/ui/Button";
import { proposeRegistrationForm } from "@/lib/api";
import type { RegistrationFormField } from "@/types";

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
  padding: "0.5rem 0.625rem",
  fontSize: "0.8rem",
  color: "#fff",
  outline: "none",
  fontFamily: "inherit",
  boxSizing: "border-box",
};

const FIELD_TYPES = ["text", "email", "tel", "url", "select", "textarea", "number", "date"];

function slugify(label: string): string {
  return (
    label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || `field_${Date.now()}`
  );
}

const DEFAULT_FIELDS: RegistrationFormField[] = [
  { field_id: "full_name", label: "Full Name", type: "text", required: true },
  { field_id: "email", label: "Email Address", type: "email", required: true, unique_per_event: true },
  { field_id: "phone", label: "Phone Number", type: "tel", required: true },
  { field_id: "college", label: "College / Institution", type: "text", required: true },
];

export default function RegistrationFormEditor({
  eventId,
  initialFields,
}: {
  eventId: string;
  initialFields?: RegistrationFormField[] | null;
}) {
  const [fields, setFields] = useState<RegistrationFormField[]>(
    initialFields && initialFields.length ? initialFields : DEFAULT_FIELDS
  );
  const [submitting, setSubmitting] = useState(false);

  const update = (idx: number, patch: Partial<RegistrationFormField>) => {
    setFields((prev) => prev.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
  };

  const addField = () =>
    setFields((prev) => [...prev, { field_id: `field_${prev.length + 1}`, label: "", type: "text", required: false }]);

  const removeField = (idx: number) => setFields((prev) => prev.filter((_, i) => i !== idx));

  const submit = async () => {
    const cleaned = fields
      .filter((f) => f.label.trim())
      .map((f) => ({
        ...f,
        field_id: f.field_id?.trim() || slugify(f.label),
        options:
          f.type === "select"
            ? (Array.isArray(f.options) ? f.options : String(f.options || "").split(",").map((s) => s.trim()).filter(Boolean))
            : undefined,
      }));
    if (cleaned.length === 0) {
      toast.error("Add at least one field with a label.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await proposeRegistrationForm(eventId, cleaned);
      toast.success(res.message || "Submitted for approval — review it in Approvals.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to submit form for approval");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={card}>
      <h2 style={{ fontSize: "0.875rem", fontWeight: 700, color: "#fff", margin: "0 0 0.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <ClipboardList size={16} color="#e8503a" /> Public Registration Form
      </h2>
      <p style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.4)", margin: "0 0 1rem" }}>
        Define the fields shown on the public registration page. Saving submits the form for
        approval — it goes live only after you approve it in the Approvals panel.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem", marginBottom: "1rem" }}>
        {fields.map((f, idx) => (
          <div
            key={idx}
            style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center", padding: "0.625rem", borderRadius: "0.5rem", background: "rgba(255,255,255,0.02)", border: "1px solid #1e1e1e" }}
          >
            <input
              value={f.label}
              onChange={(e) => update(idx, { label: e.target.value, field_id: f.field_id || slugify(e.target.value) })}
              placeholder="Field label (e.g. LinkedIn URL)"
              style={{ ...inputBase, flex: "3 1 12rem", width: "auto" }}
            />
            <select value={f.type} onChange={(e) => update(idx, { type: e.target.value })} style={{ ...inputBase, flex: "1 1 7rem", width: "auto" }}>
              {FIELD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            {f.type === "select" && (
              <input
                value={Array.isArray(f.options) ? f.options.join(", ") : (f.options as unknown as string) || ""}
                onChange={(e) => update(idx, { options: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                placeholder="Options, comma separated"
                style={{ ...inputBase, flex: "2 1 10rem", width: "auto" }}
              />
            )}
            <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.75rem", color: "rgba(255,255,255,0.6)", whiteSpace: "nowrap" }}>
              <input type="checkbox" checked={!!f.required} onChange={(e) => update(idx, { required: e.target.checked })} />
              Required
            </label>
            <button
              type="button"
              onClick={() => removeField(idx)}
              title="Remove field"
              style={{ display: "flex", height: "1.9rem", width: "1.9rem", flexShrink: 0, alignItems: "center", justifyContent: "center", borderRadius: "0.5rem", border: "1px solid #222", background: "transparent", color: "rgba(255,255,255,0.35)", cursor: "pointer" }}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <Button type="button" variant="secondary" onClick={addField}>
          <Plus size={16} /> Add Field
        </Button>
        <Button type="button" variant="primary" onClick={submit} loading={submitting}>
          <Send size={16} /> Submit Form for Approval
        </Button>
      </div>
    </div>
  );
}
