"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { useEffect } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
}

const sizeMap: Record<NonNullable<ModalProps["size"]>, string> = {
  sm: "24rem",
  md: "32rem",
  lg: "40rem",
  xl: "56rem",
};

export default function Modal({
  open,
  onClose,
  title,
  children,
  size = "md",
}: ModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (open) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(0,0,0,0.7)",
              backdropFilter: "blur(4px)",
            }}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 20 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            style={{
              position: "relative",
              zIndex: 10,
              width: "100%",
              maxWidth: sizeMap[size],
              maxHeight: "calc(100vh - 2rem)",
              overflow: "auto",
              borderRadius: "0.75rem",
              border: "1px solid #222",
              background: "#111",
              boxShadow: "0 25px 50px rgba(0,0,0,0.5)",
            }}
          >
            {title && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid #222",
                  padding: "1rem 1.5rem",
                }}
              >
                <h2
                  style={{
                    fontSize: "1.125rem",
                    fontWeight: 600,
                    color: "#fff",
                    margin: 0,
                  }}
                >
                  {title}
                </h2>
                <button
                  onClick={onClose}
                  style={{
                    display: "flex",
                    height: "2rem",
                    width: "2rem",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "0.5rem",
                    color: "rgba(255,255,255,0.4)",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  <X size={16} />
                </button>
              </div>
            )}
            <div style={{ padding: title ? "1.25rem 1.5rem" : "1.5rem" }}>
              {children}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
