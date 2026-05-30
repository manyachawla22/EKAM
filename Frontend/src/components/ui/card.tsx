"use client";

import { motion } from "framer-motion";
import { type HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  glow?: boolean;
  hoverable?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
}

const paddingMap = {
  none: "0",
  sm: "1rem",
  md: "1.5rem",
  lg: "2rem",
};

export default function Card({
  glow = false,
  hoverable = false,
  padding = "md",
  className,
  children,
  onClick,
  style,
}: CardProps) {
  const baseStyle: React.CSSProperties = {
    borderRadius: "0.75rem",
    border: "1px solid #222",
    background: "#111",
    padding: paddingMap[padding],
    cursor: hoverable ? "pointer" : undefined,
    transition: "box-shadow 0.3s ease, border-color 0.3s ease",
    ...style,
  };

  if (hoverable) {
    return (
      <motion.div
        whileHover={{ y: -2 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        style={baseStyle}
        onClick={onClick}
        className={glow ? `card-glow ${className || ""}` : className}
      >
        {children}
      </motion.div>
    );
  }

  return (
    <div
      style={baseStyle}
      onClick={onClick}
      className={glow ? `card-glow ${className || ""}` : className}
    >
      {children}
    </div>
  );
}
