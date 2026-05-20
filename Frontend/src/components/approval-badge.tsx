"use client";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type ApprovalStatus = "approved" | "pending" | "rejected" | "in_progress" | "completed" | "flagged" | "ready" | "draft";

const statusConfig: Record<ApprovalStatus, { label: string; className: string }> = {
  approved: { label: "Approved", className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" },
  pending: { label: "Pending", className: "bg-amber-500/10 text-amber-500 border-amber-500/20" },
  rejected: { label: "Rejected", className: "bg-red-500/10 text-red-500 border-red-500/20" },
  in_progress: { label: "In Progress", className: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
  completed: { label: "Completed", className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" },
  flagged: { label: "Flagged", className: "bg-red-500/10 text-red-500 border-red-500/20" },
  ready: { label: "Ready", className: "bg-primary/10 text-primary border-primary/20" },
  draft: { label: "Draft", className: "bg-muted text-muted-foreground border-border" },
};

export function ApprovalBadge({ status, className }: { status: ApprovalStatus; className?: string }) {
  const config = statusConfig[status] || statusConfig.pending;
  return (
    <Badge variant="outline" className={cn("text-[11px] font-medium", config.className, className)}>
      <span className={cn("mr-1.5 h-1.5 w-1.5 rounded-full inline-block", {
        "bg-emerald-500": status === "approved" || status === "completed",
        "bg-amber-500": status === "pending",
        "bg-red-500": status === "rejected" || status === "flagged",
        "bg-blue-500": status === "in_progress",
        "bg-primary": status === "ready",
        "bg-muted-foreground": status === "draft",
      })} />
      {config.label}
    </Badge>
  );
}
