"use client";

import { type InputHTMLAttributes, forwardRef } from "react";

const wrapperStyle = (fullWidth: boolean): React.CSSProperties => ({
  display: "flex",
  flexDirection: "column",
  gap: "0.375rem",
  width: fullWidth ? "100%" : "auto",
});

const labelStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  fontWeight: 500,
  color: "rgba(255,255,255,0.8)",
};

const fieldBaseStyle = (
  fullWidth: boolean,
  error: boolean
): React.CSSProperties => ({
  width: fullWidth ? "100%" : undefined,
  borderRadius: "0.5rem",
  border: `1px solid ${error ? "rgba(239,68,68,0.6)" : "#222"}`,
  background: "#0d0d0d",
  padding: "0.625rem 1rem",
  fontSize: "0.875rem",
  color: "#fff",
  outline: "none",
  transition: "all 0.2s",
  fontFamily: "inherit",
  boxSizing: "border-box",
});

const hintStyle = (isError: boolean): React.CSSProperties => ({
  fontSize: "0.75rem",
  color: isError ? "#f87171" : "rgba(255,255,255,0.4)",
  margin: 0,
});

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  fullWidth?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, fullWidth = false, style, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div style={wrapperStyle(fullWidth)}>
        {label && (
          <label htmlFor={inputId} style={labelStyle}>
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          style={{ ...fieldBaseStyle(fullWidth, !!error), ...style }}
          {...props}
        />
        {error && <p style={hintStyle(true)}>{error}</p>}
        {hint && !error && <p style={hintStyle(false)}>{hint}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;

// ─── Textarea ─────────────────────────────────────────────────────────────────
interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  fullWidth?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, hint, fullWidth = false, style, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div style={wrapperStyle(fullWidth)}>
        {label && (
          <label htmlFor={inputId} style={labelStyle}>
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          style={{
            ...fieldBaseStyle(fullWidth, !!error),
            resize: "vertical",
            minHeight: "100px",
            ...style,
          }}
          {...props}
        />
        {error && <p style={hintStyle(true)}>{error}</p>}
        {hint && !error && <p style={hintStyle(false)}>{hint}</p>}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";

// ─── Select ───────────────────────────────────────────────────────────────────
interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
  fullWidth?: boolean;
  options: { value: string; label: string }[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    { label, error, hint, fullWidth = false, style, id, options, ...props },
    ref
  ) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div style={wrapperStyle(fullWidth)}>
        {label && (
          <label htmlFor={inputId} style={labelStyle}>
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={inputId}
          style={{ ...fieldBaseStyle(fullWidth, !!error), ...style }}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} style={{ background: "#111" }}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <p style={hintStyle(true)}>{error}</p>}
        {hint && !error && <p style={hintStyle(false)}>{hint}</p>}
      </div>
    );
  }
);

Select.displayName = "Select";
