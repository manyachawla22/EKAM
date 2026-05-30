"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring" as const, stiffness: 100, damping: 20 },
  },
};

const letterVariants = {
  hidden: { opacity: 0, y: 80, rotateX: -90 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    rotateX: 0,
    transition: {
      delay: 0.1 + i * 0.08,
      type: "spring" as const,
      stiffness: 200,
      damping: 18,
    },
  }),
};

export default function HeroSection() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [0, 200]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  // Mouse parallax
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 2;
      const y = (e.clientY / window.innerHeight - 0.5) * 2;
      setMouse({ x, y });
    };
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, []);

  const letters = "EKAM".split("");

  return (
    <section
      ref={ref}
      className="grid-bg"
      style={{ position: "relative", minHeight: "100vh", overflow: "hidden" }}
    >
      {/* Floating orb — top left, follows mouse */}
      <motion.div
        className="pointer-events-none rounded-full"
        style={{
          position: "absolute",
          top: "-8rem",
          left: "-8rem",
          width: "28rem",
          height: "28rem",
          background:
            "radial-gradient(circle, rgba(232,80,58,0.25) 0%, rgba(232,80,58,0.08) 50%, transparent 70%)",
          x: mouse.x * 30,
          y: mouse.y * 30,
        }}
        animate={{ scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Secondary orb — bottom right, follows mouse opposite */}
      <motion.div
        className="pointer-events-none rounded-full"
        style={{
          position: "absolute",
          bottom: "-10rem",
          right: "-10rem",
          width: "34rem",
          height: "34rem",
          background:
            "radial-gradient(circle, rgba(232,80,58,0.15) 0%, rgba(232,80,58,0.04) 50%, transparent 70%)",
          x: -mouse.x * 40,
          y: -mouse.y * 40,
        }}
        animate={{ scale: [1.1, 1, 1.1], opacity: [0.4, 0.8, 0.4] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Mid blue accent orb */}
      <motion.div
        className="pointer-events-none rounded-full"
        style={{
          position: "absolute",
          top: "40%",
          right: "10%",
          width: "20rem",
          height: "20rem",
          background:
            "radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)",
          x: mouse.x * 20,
          y: mouse.y * 20,
        }}
        animate={{ scale: [1, 1.3, 1] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Animated horizontal beams */}
      <motion.div
        className="pointer-events-none"
        style={{ position: "absolute", inset: 0 }}
      >
        <motion.div
          style={{
            position: "absolute",
            top: "25%",
            left: 0,
            right: 0,
            height: "1px",
            background:
              "linear-gradient(to right, transparent, rgba(232,80,58,0.4), transparent)",
          }}
          animate={{ opacity: [0.2, 0.8, 0.2] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          style={{
            position: "absolute",
            top: "75%",
            left: 0,
            right: 0,
            height: "1px",
            background:
              "linear-gradient(to right, transparent, rgba(99,102,241,0.3), transparent)",
          }}
          animate={{ opacity: [0.1, 0.5, 0.1] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        />
      </motion.div>

      {/* Floating tiny dots */}
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={i}
          style={{
            position: "absolute",
            top: `${15 + i * 9}%`,
            left: `${5 + (i * 11) % 90}%`,
            width: "4px",
            height: "4px",
            borderRadius: "9999px",
            background: i % 2 === 0 ? "#e8503a" : "rgba(255,255,255,0.4)",
            boxShadow: i % 2 === 0 ? "0 0 10px #e8503a" : "0 0 6px rgba(255,255,255,0.4)",
          }}
          animate={{
            y: [0, -30, 0],
            opacity: [0.3, 1, 0.3],
          }}
          transition={{
            duration: 3 + (i % 3),
            repeat: Infinity,
            ease: "easeInOut",
            delay: i * 0.3,
          }}
        />
      ))}

      {/* Content wrapper */}
      <motion.div
        style={{
          y,
          opacity,
          position: "relative",
          zIndex: 10,
          width: "100%",
          maxWidth: "80rem",
          marginLeft: "auto",
          marginRight: "auto",
          paddingLeft: "1.5rem",
          paddingRight: "1.5rem",
          paddingTop: "10rem",
          paddingBottom: "8rem",
        }}
      >
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          style={{
            width: "100%",
            maxWidth: "64rem",
            marginLeft: "auto",
            marginRight: "auto",
            textAlign: "center",
          }}
        >
          {/* Tag pill */}
          <motion.div variants={itemVariants} style={{ marginBottom: "2rem" }}>
            <motion.span
              whileHover={{ scale: 1.05 }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                borderRadius: "9999px",
                border: "1px solid rgba(232,80,58,0.3)",
                background: "rgba(232,80,58,0.1)",
                padding: "0.375rem 1rem",
                fontSize: "0.875rem",
                color: "#e8503a",
              }}
            >
              <motion.span
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                animate={{ rotate: 360 }}
                transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
              >
                <Sparkles size={12} />
              </motion.span>
              Event Management Reimagined
            </motion.span>
          </motion.div>

          {/* EKAM letter-by-letter */}
          <div
            style={{
              perspective: "1000px",
              display: "flex",
              justifyContent: "center",
              gap: "0.05em",
            }}
          >
            {letters.map((letter, i) => (
              <motion.span
                key={i}
                custom={i}
                variants={letterVariants}
                whileHover={{
                  scale: 1.1,
                  color: "#e8503a",
                  textShadow: "0 0 40px rgba(232,80,58,0.8)",
                  transition: { duration: 0.2 },
                }}
                style={{
                  display: "inline-block",
                  fontSize: "clamp(5rem, 15vw, 12rem)",
                  fontWeight: 900,
                  fontStyle: "italic",
                  lineHeight: 1,
                  letterSpacing: "-0.04em",
                  color: "#ffffff",
                  cursor: "default",
                  textShadow: "0 0 60px rgba(232,80,58,0.15)",
                }}
              >
                {letter}
              </motion.span>
            ))}
          </div>

          {/* Animated gradient subtitle */}
          <motion.p
            variants={itemVariants}
            style={{
              marginTop: "0.75rem",
              fontSize: "clamp(1.5rem, 4vw, 2.5rem)",
              fontWeight: 700,
              fontStyle: "italic",
              letterSpacing: "0.02em",
              background:
                "linear-gradient(90deg, #e8503a, #ff9580, #e8503a)",
              backgroundSize: "200% auto",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              animation: "shimmer 4s linear infinite",
            }}
          >
            Organize. Compete. Excel.
          </motion.p>

          {/* Description */}
          <motion.p
            variants={itemVariants}
            style={{
              marginTop: "1.5rem",
              maxWidth: "42rem",
              marginLeft: "auto",
              marginRight: "auto",
              fontSize: "1.125rem",
              lineHeight: 1.6,
              color: "rgba(255,255,255,0.55)",
            }}
          >
            The all-in-one platform for running hackathons, coding contests, and
            team challenges. AI-powered event creation, smart team formation, and
            seamless judge management — all in one place.
          </motion.p>

          {/* CTA buttons */}
          <motion.div
            variants={itemVariants}
            style={{
              marginTop: "2.5rem",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "center",
              gap: "1rem",
            }}
          >
            <Link href="/signup">
              <motion.button
                whileHover={{
                  scale: 1.04,
                  boxShadow: "0 0 40px rgba(232,80,58,0.6)",
                }}
                whileTap={{ scale: 0.96 }}
                style={{
                  position: "relative",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  borderRadius: "0.75rem",
                  background: "#e8503a",
                  padding: "1rem 2rem",
                  fontSize: "1.125rem",
                  fontWeight: 600,
                  color: "#fff",
                  border: "none",
                  cursor: "pointer",
                  boxShadow: "0 10px 30px rgba(232,80,58,0.3)",
                  overflow: "hidden",
                }}
              >
                <span style={{ position: "relative", zIndex: 1 }}>Get Started</span>
                <motion.span
                  style={{ position: "relative", zIndex: 1, display: "flex" }}
                  animate={{ x: [0, 4, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                >
                  <ArrowRight size={20} />
                </motion.span>
                {/* Shine effect */}
                <motion.div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background:
                      "linear-gradient(120deg, transparent 30%, rgba(255,255,255,0.3) 50%, transparent 70%)",
                    pointerEvents: "none",
                  }}
                  animate={{ x: ["-100%", "200%"] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", repeatDelay: 1 }}
                />
              </motion.button>
            </Link>

            <Link href="/login">
              <motion.button
                whileHover={{ scale: 1.04, borderColor: "rgba(255,255,255,0.5)" }}
                whileTap={{ scale: 0.96 }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  borderRadius: "0.75rem",
                  border: "1px solid rgba(255,255,255,0.2)",
                  background: "transparent",
                  padding: "1rem 2rem",
                  fontSize: "1.125rem",
                  fontWeight: 600,
                  color: "#fff",
                  cursor: "pointer",
                  transition: "border-color 0.2s",
                }}
              >
                Sign In
              </motion.button>
            </Link>
          </motion.div>

          {/* Stats */}
          <motion.div
            variants={itemVariants}
            style={{
              marginTop: "4rem",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "center",
              gap: "3rem",
            }}
          >
            {[
              { value: "AI-Powered", label: "Event Creation" },
              { value: "Smart", label: "Team Formation" },
              { value: "Real-time", label: "Evaluations" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                whileHover={{ y: -4 }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 + i * 0.1 }}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  cursor: "default",
                }}
              >
                <motion.span
                  style={{
                    fontSize: "1.5rem",
                    fontWeight: 700,
                    color: "#e8503a",
                  }}
                  animate={{ textShadow: ["0 0 0px rgba(232,80,58,0)", "0 0 20px rgba(232,80,58,0.6)", "0 0 0px rgba(232,80,58,0)"] }}
                  transition={{ duration: 3, repeat: Infinity, delay: i * 0.5 }}
                >
                  {stat.value}
                </motion.span>
                <span style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.4)" }}>
                  {stat.label}
                </span>
              </motion.div>
            ))}
          </motion.div>

          {/* Scroll indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            style={{
              marginTop: "5rem",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)", letterSpacing: "0.15em", textTransform: "uppercase" }}>
              Scroll
            </span>
            <motion.div
              style={{
                width: "1.5rem",
                height: "2.5rem",
                borderRadius: "9999px",
                border: "2px solid rgba(255,255,255,0.2)",
                display: "flex",
                justifyContent: "center",
                paddingTop: "0.375rem",
              }}
            >
              <motion.div
                style={{
                  width: "4px",
                  height: "8px",
                  borderRadius: "9999px",
                  background: "#e8503a",
                }}
                animate={{ y: [0, 12, 0], opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              />
            </motion.div>
          </motion.div>
        </motion.div>
      </motion.div>

      {/* Bottom fade */}
      <div
        className="pointer-events-none"
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "10rem",
          background: "linear-gradient(to top, #0a0a0a, transparent)",
        }}
      />
    </section>
  );
}
