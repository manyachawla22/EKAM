"use client";

import type { RegistrationFormField } from "@/types";

interface Props {
  field: RegistrationFormField;
  value: unknown;
  prefilled?: boolean;
  onChange: (value: unknown) => void;
}

const inputClass =
  "w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:border-[#e8503a]/50 focus:bg-white/[0.05]";

/** Renders one registration-form field based on its declared `type`. */
export default function DynamicField({ field, value, prefilled, onChange }: Props) {
  const v = value ?? "";
  const t = (field.type || "text").toLowerCase();

  return (
    <div>
      <label className="mb-1.5 flex flex-wrap items-center gap-2 text-sm font-medium text-white/80">
        {field.label}
        {field.required && <span className="text-[#e8503a]">*</span>}
        {prefilled && (
          <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-normal text-emerald-400">
            auto-filled — please verify
          </span>
        )}
      </label>

      {t === "select" ? (
        <select
          className={inputClass}
          value={String(v)}
          required={field.required}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="" className="bg-[#0a0a0a]">
            Select…
          </option>
          {(field.options || []).map((opt) => (
            <option key={opt} value={opt} className="bg-[#0a0a0a]">
              {opt}
            </option>
          ))}
        </select>
      ) : t === "textarea" ? (
        <textarea
          className={inputClass}
          rows={3}
          value={String(v)}
          required={field.required}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          className={inputClass}
          type={
            t === "email"
              ? "email"
              : t === "tel"
              ? "tel"
              : t === "url"
              ? "url"
              : t === "number"
              ? "number"
              : t === "date"
              ? "date"
              : "text"
          }
          value={String(v)}
          required={field.required}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </div>
  );
}
