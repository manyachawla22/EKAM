"use client";

export const dynamic = "force-dynamic";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, CheckCircle, XCircle, Star, Hash, Mail } from "lucide-react";
import { toast } from "sonner";
import { getJudgeInvite, respondJudgeInvite } from "@/lib/api";
import type { JudgeInviteDetail } from "@/lib/api";
import ParticleBackground from "@/components/landing/ParticleBackground";
import Button from "@/components/ui/Button";
import Link from "next/link";

type Stage = "loading" | "pending" | "responding" | "accepted" | "declined" | "error" | "already_responded";

function JudgeInviteContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [stage, setStage] = useState<Stage>("loading");
  const [invite, setInvite] = useState<JudgeInviteDetail | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (!token) {
      setErrorMsg("No invite token found in this link.");
      setStage("error");
      return;
    }
    getJudgeInvite(token)
      .then((data) => {
        setInvite(data);
        if (data.invite_status === "accepted") setStage("already_responded");
        else if (data.invite_status === "declined") setStage("already_responded");
        else setStage("pending");
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "This invite link is invalid or has expired.");
        setStage("error");
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRespond = async (accepted: boolean) => {
    if (!token) return;
    setStage("responding");
    try {
      const result = await respondJudgeInvite(token, accepted);
      setInvite(result);
      setStage(accepted ? "accepted" : "declined");
      toast.success(accepted ? "Invitation accepted!" : "Invitation declined.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to process your response.";
      toast.error(msg);
      setStage("pending");
    }
  };

  return (
    <div style={{
      position: "relative", minHeight: "100vh", overflow: "hidden",
      background: "#0a0a0a", display: "flex", alignItems: "center",
      justifyContent: "center", padding: "1rem",
    }}>
      <ParticleBackground />
      <div className="grid-bg" style={{ position: "absolute", inset: 0, opacity: 0.4, pointerEvents: "none" }} />

      <motion.div
        style={{ position: "absolute", top: "25%", left: "20%", height: "20rem", width: "20rem", borderRadius: "9999px", background: "rgba(168,85,247,0.08)", filter: "blur(80px)", pointerEvents: "none" }}
        animate={{ x: [0, 50, 0], y: [0, -30, 0], scale: [1, 1.15, 1] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />

      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: "spring", stiffness: 180, damping: 22 }}
        style={{ position: "relative", zIndex: 10, width: "100%", maxWidth: "26rem" }}
      >
        <motion.div
          style={{
            position: "absolute", inset: -2, borderRadius: "1rem",
            background: "linear-gradient(135deg, rgba(168,85,247,0.3), rgba(168,85,247,0.05), rgba(168,85,247,0.3))",
            filter: "blur(20px)", opacity: 0.5, pointerEvents: "none",
          }}
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />

        <div style={{
          position: "relative", borderRadius: "1rem", border: "1px solid #222",
          background: "rgba(17,17,17,0.97)", backdropFilter: "blur(12px)",
          padding: "2.5rem 2rem", boxShadow: "0 25px 50px rgba(0,0,0,0.6)",
        }}>
          {/* Logo */}
          <div style={{ display: "flex", justifyContent: "center", marginBottom: "1.75rem" }}>
            <div style={{
              display: "flex", height: "3rem", width: "3rem", alignItems: "center",
              justifyContent: "center", borderRadius: "0.75rem", background: "#c084fc",
              boxShadow: "0 0 30px rgba(168,85,247,0.5)",
            }}>
              <Zap size={24} color="white" />
            </div>
          </div>

          <AnimatePresence mode="wait">

            {/* Loading */}
            {stage === "loading" && (
              <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}
              >
                <svg style={{ animation: "spin 1s linear infinite", height: "2rem", width: "2rem", color: "#c084fc" }} viewBox="0 0 24 24" fill="none">
                  <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path style={{ opacity: 0.85 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <p style={{ color: "rgba(255,255,255,0.5)", margin: 0, fontSize: "0.9rem" }}>Loading invitation…</p>
              </motion.div>
            )}

            {/* Pending — show accept/decline */}
            {(stage === "pending" || stage === "responding") && invite && (
              <motion.div key="pending" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}
              >
                <div style={{ textAlign: "center" }}>
                  <div style={{
                    display: "inline-flex", alignItems: "center", justifyContent: "center",
                    height: "3.5rem", width: "3.5rem", borderRadius: "1rem",
                    background: "rgba(168,85,247,0.1)", border: "1px solid rgba(168,85,247,0.2)",
                    marginBottom: "1rem",
                  }}>
                    <Star size={24} color="#c084fc" />
                  </div>
                  <h1 style={{ fontSize: "1.25rem", fontWeight: 900, color: "#fff", margin: "0 0 0.35rem" }}>
                    Judge Invitation
                  </h1>
                  <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
                    You&apos;ve been invited to judge an event on EKAM
                  </p>
                </div>

                {/* Event info card */}
                <div style={{
                  borderRadius: "0.75rem", border: "1px solid rgba(168,85,247,0.2)",
                  background: "rgba(168,85,247,0.05)", padding: "1rem",
                  display: "flex", flexDirection: "column", gap: "0.6rem",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    <Zap size={14} color="#c084fc" />
                    <span style={{ fontSize: "1rem", fontWeight: 700, color: "#fff" }}>{invite.event_name}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    <Mail size={14} color="rgba(255,255,255,0.3)" />
                    <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.5)" }}>Invited as: {invite.judge_email}</span>
                  </div>
                </div>

                <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.35)", margin: 0, lineHeight: 1.6, textAlign: "center" }}>
                  Do you accept this judging invitation?
                </p>

                <div style={{ display: "flex", gap: "0.75rem" }}>
                  <button
                    onClick={() => handleRespond(false)}
                    disabled={stage === "responding"}
                    style={{
                      flex: 1, padding: "0.625rem", borderRadius: "0.5rem",
                      border: "1px solid #333", background: "transparent",
                      color: "rgba(255,255,255,0.5)", fontSize: "0.875rem", fontWeight: 600,
                      cursor: stage === "responding" ? "not-allowed" : "pointer",
                      opacity: stage === "responding" ? 0.5 : 1, transition: "all 0.2s",
                    }}
                  >
                    Decline
                  </button>
                  <Button
                    variant="primary"
                    loading={stage === "responding"}
                    onClick={() => handleRespond(true)}
                    style={{ flex: 1, background: "#c084fc", borderColor: "#c084fc" } as React.CSSProperties}
                  >
                    Accept
                  </Button>
                </div>
              </motion.div>
            )}

            {/* Accepted */}
            {stage === "accepted" && invite && (
              <motion.div key="accepted" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1.25rem", textAlign: "center" }}
              >
                <CheckCircle size={48} color="#4ade80" />
                <div>
                  <h2 style={{ fontSize: "1.25rem", fontWeight: 800, color: "#fff", margin: "0 0 0.35rem" }}>
                    You&apos;re in!
                  </h2>
                  <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
                    You&apos;ve accepted the judging invitation for <strong style={{ color: "#fff" }}>{invite.event_name}</strong>.
                  </p>
                </div>

                {/* Login credentials */}
                <div style={{
                  width: "100%", borderRadius: "0.75rem", border: "1px solid rgba(34,197,94,0.2)",
                  background: "rgba(34,197,94,0.06)", padding: "1rem",
                  display: "flex", flexDirection: "column", gap: "0.75rem",
                }}>
                  <p style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "rgba(255,255,255,0.3)", margin: 0 }}>
                    Your login credentials
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                        <Hash size={12} /> Event Hash
                      </span>
                      <code style={{
                        fontSize: "0.875rem", fontWeight: 700, color: "#4ade80",
                        background: "rgba(34,197,94,0.1)", padding: "0.2rem 0.5rem", borderRadius: "0.375rem",
                      }}>
                        {invite.event_hash}
                      </code>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                        <Mail size={12} /> Email
                      </span>
                      <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.7)" }}>{invite.judge_email}</span>
                    </div>
                  </div>
                </div>

                <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)", margin: 0, lineHeight: 1.6 }}>
                  Go to login, select <strong style={{ color: "rgba(255,255,255,0.5)" }}>Participant / Judge</strong>, enter the event hash and your email, then request your OTP.
                </p>

                <Link href="/login" style={{
                  display: "block", width: "100%", padding: "0.625rem",
                  borderRadius: "0.5rem", background: "#c084fc", color: "#fff",
                  fontSize: "0.875rem", fontWeight: 700, textAlign: "center", textDecoration: "none",
                }}>
                  Go to Login
                </Link>
              </motion.div>
            )}

            {/* Declined */}
            {stage === "declined" && invite && (
              <motion.div key="declined" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem", textAlign: "center" }}
              >
                <XCircle size={48} color="#f87171" />
                <div>
                  <h2 style={{ fontSize: "1.25rem", fontWeight: 800, color: "#fff", margin: "0 0 0.35rem" }}>
                    Invitation Declined
                  </h2>
                  <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>
                    You&apos;ve declined the invitation for <strong style={{ color: "#fff" }}>{invite.event_name}</strong>.
                  </p>
                </div>
                <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.3)", margin: 0 }}>
                  The organizer will be notified. You can close this page.
                </p>
              </motion.div>
            )}

            {/* Already responded */}
            {stage === "already_responded" && invite && (
              <motion.div key="already" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem", textAlign: "center" }}
              >
                {invite.invite_status === "accepted" ? (
                  <CheckCircle size={40} color="#4ade80" />
                ) : (
                  <XCircle size={40} color="#f87171" />
                )}
                <p style={{ color: "#fff", fontWeight: 700, margin: 0 }}>
                  You already {invite.invite_status} this invitation.
                </p>
                {invite.invite_status === "accepted" && (
                  <Link href="/login" style={{
                    padding: "0.5rem 1.5rem", borderRadius: "0.5rem",
                    background: "#c084fc", color: "#fff",
                    fontSize: "0.875rem", fontWeight: 700, textDecoration: "none",
                  }}>
                    Go to Login
                  </Link>
                )}
              </motion.div>
            )}

            {/* Error */}
            {stage === "error" && (
              <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem", textAlign: "center" }}
              >
                <XCircle size={40} color="#f87171" />
                <p style={{ color: "#fff", fontWeight: 700, margin: 0 }}>Invalid invite link</p>
                <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.4)", margin: 0 }}>{errorMsg}</p>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}

export default function JudgeInvitePage() {
  return (
    <Suspense fallback={null}>
      <JudgeInviteContent />
    </Suspense>
  );
}
