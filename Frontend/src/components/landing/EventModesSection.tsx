"use client";

import { motion, useInView, useMotionValue, useTransform, useSpring } from "framer-motion";
import { useRef } from "react";
import { Code2, Cpu, Users } from "lucide-react";

type Mode = {
  id: number;
  title: string;
  subtitle: string;
  description: string;
  icon: React.ReactNode;
  gradientFrom: string;
  gradientTo: string;
  accent: string;
  featured: boolean;
};

const modes: Mode[] = [
  {
    id: 1,
    title: "Hackathon",
    subtitle: "Build & Ship",
    description:
      "72-hour intensive build events with multi-round judging, team formation, and real-time submission tracking.",
    icon: <Cpu className="h-8 w-8" />,
    gradientFrom: "#1a0a05",
    gradientTo: "#2a0f08",
    accent: "#e8503a",
    featured: false,
  },
  {
    id: 2,
    title: "Coding Contest",
    subtitle: "Code Fast. Code Smart.",
    description:
      "Individual or team competitive programming with automated scoring, leaderboards, and AI-assisted problem curation.",
    icon: <Code2 className="h-8 w-8" />,
    gradientFrom: "#0d0d1a",
    gradientTo: "#121225",
    accent: "#6366f1",
    featured: false,
  },
  {
    id: 3,
    title: "Team Challenge",
    subtitle: "Collaborate & Conquer",
    description:
      "Long-form collaborative events with smart auto-team formation based on skills, multi-stage rounds, and peer evaluations.",
    icon: <Users className="h-8 w-8" />,
    gradientFrom: "#050d0a",
    gradientTo: "#091a14",
    accent: "#22c55e",
    featured: true,
  },
];

function TiltCard({ mode, index, inView }: { mode: Mode; index: number; inView: boolean }) {
  const cardRef = useRef<HTMLDivElement>(null);

  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const rotateX = useSpring(useTransform(mouseY, [-100, 100], [8, -8]), {
    stiffness: 300,
    damping: 30,
  });
  const rotateY = useSpring(useTransform(mouseX, [-100, 100], [-8, 8]), {
    stiffness: 300,
    damping: 30,
  });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    mouseX.set(e.clientX - rect.left - rect.width / 2);
    mouseY.set(e.clientY - rect.top - rect.height / 2);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  return (
    <motion.div
      ref={cardRef}
      initial={{ opacity: 0, y: 60 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.15 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        rotateX,
        rotateY,
        transformStyle: "preserve-3d",
        position: "relative",
        borderRadius: "1rem",
        border: `1px solid ${mode.featured ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.05)"}`,
        overflow: "hidden",
        cursor: "pointer",
        background: `linear-gradient(135deg, ${mode.gradientFrom}, ${mode.gradientTo})`,
        minHeight: mode.featured ? "440px" : "380px",
        transition: "border-color 0.3s ease",
      }}
      whileHover={{
        scale: 1.02,
        borderColor: `${mode.accent}80`,
        boxShadow: `0 25px 60px ${mode.accent}30, 0 0 0 1px ${mode.accent}40`,
      }}
    >
      {/* Animated accent line at top */}
      <motion.div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "2px",
          background: mode.accent,
          transformOrigin: "left",
        }}
        initial={{ scaleX: 0 }}
        animate={inView ? { scaleX: 1 } : {}}
        transition={{ duration: 0.8, delay: 0.3 + index * 0.15, ease: "easeOut" }}
      />

      {/* Animated grid pattern */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(${mode.accent}08 1px, transparent 1px),
            linear-gradient(90deg, ${mode.accent}08 1px, transparent 1px)
          `,
          backgroundSize: "30px 30px",
          opacity: 0.4,
          pointerEvents: "none",
        }}
      />

      {/* Glow on hover */}
      <motion.div
        className="card-glow-overlay"
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background: `radial-gradient(circle at 50% 0%, ${mode.accent}35 0%, transparent 70%)`,
          opacity: 0,
          transition: "opacity 0.5s",
        }}
      />

      {/* Featured badge */}
      {mode.featured && (
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={inView ? { scale: 1, rotate: 0 } : {}}
          transition={{ delay: 0.6, type: "spring", stiffness: 200 }}
          style={{
            position: "absolute",
            top: "1rem",
            right: "1rem",
            borderRadius: "9999px",
            padding: "0.25rem 0.75rem",
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "#ffffff",
            background: mode.accent,
            boxShadow: `0 0 20px ${mode.accent}80`,
            transform: "translateZ(20px)",
          }}
        >
          ⭐ Popular
        </motion.div>
      )}

      {/* Inner content */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          padding: "2rem",
          position: "relative",
          zIndex: 1,
          transform: "translateZ(20px)",
        }}
      >
        {/* Animated icon */}
        <motion.div
          whileHover={{ rotate: [0, -10, 10, 0], scale: 1.1 }}
          transition={{ duration: 0.5 }}
          style={{
            display: "flex",
            height: "3.5rem",
            width: "3.5rem",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: "0.75rem",
            background: `${mode.accent}20`,
            color: mode.accent,
            border: `1px solid ${mode.accent}40`,
            boxShadow: `0 0 20px ${mode.accent}30`,
          }}
        >
          {mode.icon}
        </motion.div>

        {/* Spacer */}
        <div style={{ flex: 1, minHeight: "4rem" }} />

        {/* Text content */}
        <div>
          <motion.p
            initial={{ opacity: 0, x: -10 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.4 + index * 0.15 }}
            style={{
              marginBottom: "0.25rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              color: mode.accent,
            }}
          >
            {mode.subtitle}
          </motion.p>
          <motion.h3
            initial={{ opacity: 0, x: -10 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.45 + index * 0.15 }}
            style={{
              marginBottom: "0.75rem",
              fontSize: "1.75rem",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#ffffff",
            }}
          >
            {mode.title}
          </motion.h3>
          <motion.p
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.5 + index * 0.15 }}
            style={{
              fontSize: "0.875rem",
              lineHeight: 1.6,
              color: "rgba(255,255,255,0.6)",
            }}
          >
            {mode.description}
          </motion.p>
        </div>
      </div>
    </motion.div>
  );
}

export default function EventModesSection() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section
      ref={ref}
      style={{
        position: "relative",
        overflow: "hidden",
        background: "#0a0a0a",
        paddingTop: "6rem",
        paddingBottom: "6rem",
      }}
    >
      {/* Background grid + accents */}
      <div
        className="grid-bg pointer-events-none"
        style={{ position: "absolute", inset: 0, opacity: 0.5 }}
      />

      <motion.div
        style={{
          position: "absolute",
          top: "-10rem",
          left: "50%",
          transform: "translateX(-50%)",
          width: "30rem",
          height: "30rem",
          borderRadius: "9999px",
          background: "radial-gradient(circle, rgba(232,80,58,0.08) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
        animate={{ scale: [1, 1.3, 1] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />

      <div
        style={{
          position: "relative",
          zIndex: 10,
          width: "100%",
          maxWidth: "80rem",
          marginLeft: "auto",
          marginRight: "auto",
          paddingLeft: "1.5rem",
          paddingRight: "1.5rem",
        }}
      >
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          style={{ marginBottom: "4rem", textAlign: "center" }}
        >
          <motion.p
            initial={{ opacity: 0, letterSpacing: "0em" }}
            animate={inView ? { opacity: 1, letterSpacing: "0.15em" } : {}}
            transition={{ duration: 0.8 }}
            style={{
              marginBottom: "0.75rem",
              fontSize: "0.875rem",
              fontWeight: 600,
              textTransform: "uppercase",
              color: "#e8503a",
            }}
          >
            Event Types
          </motion.p>
          <h2
            style={{
              fontSize: "clamp(2.25rem, 5vw, 3.5rem)",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#ffffff",
              margin: 0,
              lineHeight: 1.1,
            }}
          >
            Choose Your{" "}
            <span
              style={{
                background: "linear-gradient(90deg, #e8503a, #ff9580, #e8503a)",
                backgroundSize: "200% auto",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                animation: "shimmer 4s linear infinite",
              }}
            >
              Arena
            </span>
          </h2>
          <p
            style={{
              marginTop: "1rem",
              color: "rgba(255,255,255,0.5)",
              maxWidth: "36rem",
              marginLeft: "auto",
              marginRight: "auto",
            }}
          >
            From rapid-fire hackathons to long-form team challenges — EKAM
            handles every format with ease.
          </p>
        </motion.div>

        {/* Cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "1.5rem",
            alignItems: "stretch",
            perspective: "1500px",
          }}
        >
          {modes.map((mode, i) => (
            <TiltCard key={mode.id} mode={mode} index={i} inView={inView} />
          ))}
        </div>
      </div>
    </section>
  );
}
