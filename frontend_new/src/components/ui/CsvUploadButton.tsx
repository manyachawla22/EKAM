"use client";

import { useRef, useState } from "react";
import { Upload, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface CsvUploadButtonProps {
  /**
   * Called with the selected file. Resolves with whatever success response
   * the parent wants to surface. Should throw an Error with a human message
   * on failure (apiFetch already does this).
   */
  onUpload: (file: File) => Promise<{ message?: string; count?: number }>;
  /**
   * Called after a successful upload so the parent can re-fetch its list.
   */
  onUploaded?: () => void;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export default function CsvUploadButton({
  onUpload,
  onUploaded,
  label = "Bulk Import CSV",
  disabled = false,
}: CsvUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);

  const triggerPicker = () => {
    if (busy || disabled) return;
    inputRef.current?.click();
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset the input so picking the same file twice re-triggers onChange.
    if (inputRef.current) inputRef.current.value = "";
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".csv")) {
      toast.error("Please choose a .csv file");
      return;
    }

    setBusy(true);
    try {
      const result = await onUpload(file);
      const count =
        typeof result?.count === "number" ? result.count : undefined;
      toast.success(
        result?.message || (count != null ? `Imported ${count} rows` : "Uploaded")
      );
      onUploaded?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        onChange={handleChange}
        style={{ display: "none" }}
      />
      <button
        type="button"
        onClick={triggerPicker}
        disabled={busy || disabled}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.5rem",
          borderRadius: "0.5rem",
          border: "1px solid rgba(255,255,255,0.18)",
          background: "transparent",
          color: "#fff",
          fontSize: "0.875rem",
          fontWeight: 500,
          padding: "0.55rem 1rem",
          cursor: busy || disabled ? "not-allowed" : "pointer",
          opacity: busy || disabled ? 0.6 : 1,
          transition: "background 0.15s, border-color 0.15s",
        }}
      >
        {busy ? (
          <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
        ) : (
          <Upload size={14} />
        )}
        <span>{busy ? "Uploading…" : label}</span>
        <FileText
          size={12}
          style={{ opacity: 0.5, marginLeft: "0.2rem" }}
        />
      </button>
    </>
  );
}
