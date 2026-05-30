import { clsx } from "clsx";
import type { EventStatus, EventStage, RoundStatus } from "@/types";

type BadgeVariant =
  | "default"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "purple";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-white/10 text-white/70 border-white/10",
  success: "bg-green-500/15 text-green-400 border-green-500/20",
  warning: "bg-yellow-500/15 text-yellow-400 border-yellow-500/20",
  danger: "bg-red-500/15 text-red-400 border-red-500/20",
  info: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  purple: "bg-purple-500/15 text-purple-400 border-purple-500/20",
};

export default function Badge({
  children,
  variant = "default",
  className,
}: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

// Helper function for event status badges
export function EventStatusBadge({ status }: { status: EventStatus }) {
  const variantMap: Record<EventStatus, BadgeVariant> = {
    draft: "default",
    active: "success",
    completed: "info",
    cancelled: "danger",
  };
  return <Badge variant={variantMap[status]}>{status}</Badge>;
}

// Helper function for event stage badges
export function EventStageBadge({ stage }: { stage: EventStage }) {
  const variantMap: Record<EventStage, BadgeVariant> = {
    registration: "info",
    team_formation: "purple",
    submission: "warning",
    evaluation: "warning",
    results: "success",
  };
  const labelMap: Record<EventStage, string> = {
    registration: "Registration",
    team_formation: "Team Formation",
    submission: "Submission",
    evaluation: "Evaluation",
    results: "Results",
  };
  return (
    <Badge variant={variantMap[stage]}>{labelMap[stage]}</Badge>
  );
}

// Helper for round status badges
export function RoundStatusBadge({ status }: { status: RoundStatus }) {
  const variantMap: Record<RoundStatus, BadgeVariant> = {
    upcoming: "default",
    active: "success",
    completed: "info",
  };
  return <Badge variant={variantMap[status]}>{status}</Badge>;
}
