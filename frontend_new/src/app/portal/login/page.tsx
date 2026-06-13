"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Zap, CheckCircle, XCircle } from "lucide-react";
import { toast } from "sonner";
import { verifyMagicLink, getMe, getRoleDashboard } from "@/lib/api";
import ParticleBackground from "@/components/landing/ParticleBackground";
import Link from "next/link";

type Status = "verifying" | "success" | "error";

export default function PortalLoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<Status>("verifying");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");

    if (!token) {
      setErrorMsg("No login token found in this link. Please request a new one.");
      setStatus("error");
      return;
    }

    const verify = async () => {
      try {
        await verifyMagicLink(token);
        // EKAM JWT is stored inside verifyMagicLink; now fetch profile
        const profile = await getMe();
        setStatus("success");
        toast.success("Logged in successfully!");
        // Honor an explicit `next` path (e.g. a magic link that points a judge
        // straight to their anomalies page); only internal paths are allowed.
        const nextParam = searchParams.get("next");
        const dest =
          nextParam && nextParam.startsWith("/")
            ? nextParam
            : getRoleDashboard(
                profile.role as Parameters<typeof getRoleDashboard>[0]
              );
        // Small delay so the user sees the success state before redirect
        setTimeout(() => {
          router.push(dest);
        }, 1200);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "This link is invalid or has expired.";
        setErrorMsg(message);
        setStatus("error");
      }
    };

    verify();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      style={{
        position: "relative",
        minHeight: "100vh",
        overflow: "hidden",
        background: "#0a0a0a",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
      }}
    >
      <ParticleBackground />
      <div
        className="grid-bg"
        style={{ position: "absolute", inset: 0, opacity: 0.4, pointerEvents: "none" }}
      />

      {/* Glow */}
      <motion.div
        style={{
          position: "absolute",
          top: "30%",
          left: "25%",
          height: "20rem",
          width: "20rem",
          borderRadius: "9999px",
          background: "rgba(232,80,58,0.1)",
          filter: "blur(80px)",
          pointerEvents: "none",
        }}
        animate={{ x: [0, 50, 0], y: [0, -30, 0], scale: [1, 1.15, 1] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
      />

      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: "spring", stiffness: 180, damping: 22 }}
        style={{
          position: "relative",
          zIndex: 10,
          width: "100%",
          maxWidth: "24rem",
        }}
      >
        {/* Outer glow */}
        <motion.div
          style={{
            position: "absolute",
            inset: -2,
            borderRadius: "1rem",
            background:
              "linear-gradient(135deg, rgba(232,80,58,0.4), rgba(232,80,58,0.1), rgba(232,80,58,0.4))",
            filter: "blur(20px)",
            opacity: 0.5,
            pointerEvents: "none",
          }}
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />

        <div
          style={{
            position: "relative",
            borderRadius: "1rem",
            border: "1px solid #222",
            background: "rgba(17,17,17,0.95)",
            backdropFilter: "blur(12px)",
            padding: "2.5rem 2rem",
            boxShadow: "0 25px 50px rgba(0,0,0,0.6)",
            textAlign: "center",
          }}
        >
          {/* Logo */}
          <motion.div
            style={{
              display: "flex",
              height: "3rem",
              width: "3rem",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "0.75rem",
              background: "#e8503a",
              boxShadow: "0 0 30px rgba(232,80,58,0.5)",
              margin: "0 auto 1.5rem",
            }}
          >
            <Zap size={24} color="white" />
          </motion.div>

          {/* Verifying state */}
          {status === "verifying" && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}
            >
              <svg
                style={{ animation: "spin 1s linear infinite", height: "2rem", width: "2rem", color: "#e8503a" }}
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  style={{ opacity: 0.85 }}
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              <p style={{ margin: 0, fontSize: "1rem", fontWeight: 600, color: "#fff" }}>
                Verifying your link&hellip;
              </p>
              <p style={{ margin: 0, fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>
                Please wait while we log you in.
              </p>
            </motion.div>
          )}

          {/* Success state */}
          {status === "success" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}
            >
              <CheckCircle size={40} color="#4ade80" />
              <p style={{ margin: 0, fontSize: "1rem", fontWeight: 600, color: "#fff" }}>
                You&apos;re in!
              </p>
              <p style={{ margin: 0, fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>
                Redirecting to your dashboard&hellip;
              </p>
            </motion.div>
          )}

          {/* Error state */}
          {status === "error" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}
            >
              <XCircle size={40} color="#f87171" />
              <p style={{ margin: 0, fontSize: "1rem", fontWeight: 600, color: "#fff" }}>
                Link invalid or expired
              </p>
              <p
                style={{
                  margin: 0,
                  fontSize: "0.8rem",
                  color: "rgba(255,255,255,0.4)",
                  lineHeight: 1.6,
                }}
              >
                {errorMsg}
              </p>
              <Link
                href="/login"
                style={{
                  marginTop: "0.5rem",
                  display: "inline-block",
                  padding: "0.5rem 1.25rem",
                  borderRadius: "0.5rem",
                  background: "#e8503a",
                  color: "#fff",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  textDecoration: "none",
                }}
              >
                Back to Login
              </Link>
            </motion.div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
