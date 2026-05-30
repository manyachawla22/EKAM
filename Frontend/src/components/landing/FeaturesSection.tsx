"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { Bot, Users, Star, Zap, Shield, BarChart } from "lucide-react";

const features = [
  {
    id: 1,
    icon: <Bot className="h-7 w-7" />,
    title: "AI Event Creation",
    subtitle: "Build events in minutes",
    description:
      "Simply chat with our AI assistant to design your event. It'll ask the right questions, configure rounds, set judging criteria, and deploy everything automatically.",
    points: ["Conversational event setup", "Auto-generates event config", "One-click deploy"],
    visualLeft: true,
    color: "#e8503a",
  },
  {
    id: 2,
    icon: <Users className="h-7 w-7" />,
    title: "Smart Team Formation",
    subtitle: "Match by skills, not luck",
    description:
      "Our algorithm groups participants based on skills, gender balance, and experience level. No more random shuffling — get balanced, diverse teams automatically.",
    points: ["Skill-based matching", "Configurable team sizes", "Handle leftovers gracefully"],
    visualLeft: false,
    color: "#6366f1",
  },
  {
    id: 3,
    icon: <Star className="h-7 w-7" />,
    title: "Judge Assignment",
    subtitle: "Fair, automated evaluation",
    description:
      "Assign judges manually or let the system auto-assign them across teams and rounds. Track scores, collect feedback, and generate comprehensive evaluation reports.",
    points: ["Auto-assign judges per team", "Round-based evaluation", "Score aggregation"],
    visualLeft: true,
    color: "#22c55e",
  },
];

const extraFeatures = [
  {
    icon: <Zap className="h-5 w-5" />,
    title: "Real-time Updates",
    description: "Live submission status and leaderboard updates.",
  },
  {
    icon: <Shield className="h-5 w-5" />,
    title: "Role-Based Access",
    description: "Organizers, judges, and participants each see only what they need.",
  },
  {
    icon: <BarChart className="h-5 w-5" />,
    title: "Detailed Reports",
    description: "Export summaries, scores, and participation data.",
  },
];

function FeatureVisual({ color, icon }: { color: string; icon: React.ReactNode }) {
  return (
    <motion.div
      whileHover={{ y: -6, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      style={{
        position: "relative",
        maxWidth: "24rem",
        marginLeft: "auto",
        marginRight: "auto",
        borderRadius: "1.5rem",
        padding: "2.5rem",
        overflow: "hidden",
        border: `1px solid ${color}30`,
        background: `linear-gradient(135deg, ${color}10, transparent)`,
        cursor: "default",
      }}
    >
      {/* Pulsing glow */}
      <motion.div
        style={{
          position: "absolute",
          top: 0,
          left: "50%",
          transform: "translateX(-50%)",
          height: "10rem",
          width: "10rem",
          borderRadius: "9999px",
          filter: "blur(60px)",
          pointerEvents: "none",
          background: `${color}50`,
        }}
        animate={{
          opacity: [0.3, 0.7, 0.3],
          scale: [1, 1.2, 1],
        }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Animated ring around icon */}
      <motion.div
        style={{
          position: "absolute",
          top: "2.5rem",
          left: "50%",
          transform: "translateX(-50%)",
          width: "7rem",
          height: "7rem",
          borderRadius: "9999px",
          border: `1px solid ${color}40`,
          pointerEvents: "none",
        }}
        animate={{ scale: [1, 1.4, 1], opacity: [0.6, 0, 0.6] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      />

      <div
        style={{
          position: "relative",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "1.5rem",
        }}
      >
        <motion.div
          whileHover={{ rotate: [0, -10, 10, 0] }}
          transition={{ duration: 0.6 }}
          style={{
            display: "flex",
            height: "5rem",
            width: "5rem",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: "1rem",
            background: `${color}25`,
            border: `1px solid ${color}50`,
            color,
            boxShadow: `0 0 30px ${color}40`,
          }}
        >
          <div style={{ transform: "scale(1.4)" }}>{icon}</div>
        </motion.div>

        {/* Animated dot grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, 1fr)",
            gap: "0.5rem",
          }}
        >
          {Array.from({ length: 20 }).map((_, j) => (
            <motion.div
              key={j}
              style={{
                height: "0.375rem",
                width: "0.375rem",
                borderRadius: "9999px",
                background: j % 3 === 0 ? color : "rgba(255,255,255,0.15)",
              }}
              animate={{
                opacity: j % 3 === 0 ? [0.4, 1, 0.4] : [0.2, 0.5, 0.2],
                scale: j % 3 === 0 ? [1, 1.5, 1] : [1, 1.1, 1],
                boxShadow: j % 3 === 0
                  ? [`0 0 0px ${color}`, `0 0 10px ${color}`, `0 0 0px ${color}`]
                  : "none",
              }}
              transition={{
                duration: 2.5,
                repeat: Infinity,
                delay: j * 0.08,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function FeatureText({
  feature,
}: {
  feature: (typeof features)[number];
}) {
  return (
    <div>
      <p
        style={{
          marginBottom: "0.5rem",
          fontSize: "0.75rem",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.15em",
          color: feature.color,
        }}
      >
        {feature.subtitle}
      </p>
      <h3
        style={{
          marginBottom: "1rem",
          fontSize: "clamp(1.875rem, 3vw, 2.25rem)",
          fontWeight: 900,
          fontStyle: "italic",
          color: "#ffffff",
        }}
      >
        {feature.title}
      </h3>
      <p
        style={{
          marginBottom: "1.5rem",
          fontSize: "1.125rem",
          lineHeight: 1.6,
          color: "rgba(255,255,255,0.5)",
        }}
      >
        {feature.description}
      </p>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {feature.points.map((point) => (
          <li
            key={point}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.7)",
              marginBottom: "0.75rem",
            }}
          >
            <span
              style={{
                display: "flex",
                height: "1.25rem",
                width: "1.25rem",
                flexShrink: 0,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "9999px",
                fontSize: "0.75rem",
                background: `${feature.color}20`,
                color: feature.color,
              }}
            >
              ✓
            </span>
            {point}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function FeaturesSection() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      ref={ref}
      style={{
        position: "relative",
        overflow: "hidden",
        background: "#060606",
        paddingTop: "6rem",
        paddingBottom: "6rem",
      }}
    >
      {/* Top + bottom hairlines */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "1px",
          background:
            "linear-gradient(to right, transparent, rgba(255,255,255,0.06), transparent)",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "1px",
          background:
            "linear-gradient(to right, transparent, rgba(255,255,255,0.06), transparent)",
        }}
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
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          style={{ marginBottom: "5rem", textAlign: "center" }}
        >
          <p
            style={{
              marginBottom: "0.75rem",
              fontSize: "0.875rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              color: "#e8503a",
            }}
          >
            Platform Features
          </p>
          <h2
            style={{
              fontSize: "clamp(2.25rem, 5vw, 3rem)",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#ffffff",
              margin: 0,
            }}
          >
            Everything You Need
          </h2>
        </motion.div>

        {/* Feature rows */}
        <div style={{ display: "flex", flexDirection: "column", gap: "7rem" }}>
          {features.map((feature, i) => (
            <motion.div
              key={feature.id}
              initial={{ opacity: 0, y: 40 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, delay: i * 0.1 }}
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                gap: "3rem",
                alignItems: "center",
              }}
            >
              {feature.visualLeft ? (
                <>
                  <FeatureVisual color={feature.color} icon={feature.icon} />
                  <FeatureText feature={feature} />
                </>
              ) : (
                <>
                  <FeatureText feature={feature} />
                  <FeatureVisual color={feature.color} icon={feature.icon} />
                </>
              )}
            </motion.div>
          ))}
        </div>

        {/* Extra feature cards */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.4 }}
          style={{
            marginTop: "6rem",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "1.25rem",
          }}
        >
          {extraFeatures.map((feat) => (
            <div
              key={feat.title}
              style={{
                borderRadius: "0.75rem",
                border: "1px solid #222",
                background: "#111",
                padding: "1.5rem",
                transition: "border-color 0.2s",
              }}
              className="hover:!border-[#e8503a]/30"
            >
              <div
                style={{
                  marginBottom: "1rem",
                  display: "flex",
                  height: "2.5rem",
                  width: "2.5rem",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "0.5rem",
                  background: "rgba(232,80,58,0.15)",
                  color: "#e8503a",
                }}
              >
                {feat.icon}
              </div>
              <h4
                style={{
                  marginBottom: "0.5rem",
                  fontWeight: 600,
                  color: "#ffffff",
                }}
              >
                {feat.title}
              </h4>
              <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.4)" }}>
                {feat.description}
              </p>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
