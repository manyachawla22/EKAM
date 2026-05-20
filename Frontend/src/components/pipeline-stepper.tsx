"use client";
import { cn } from "@/lib/utils";
import { Check, Circle, Clock } from "lucide-react";
import { motion } from "framer-motion";

interface Step {
  id: string;
  name: string;
  status: "completed" | "active" | "upcoming" | "skipped";
  completionPct?: number;
}

interface PipelineStepperProps {
  steps: Step[];
  orientation?: "horizontal" | "vertical";
  className?: string;
}

export function PipelineStepper({ steps, orientation = "horizontal", className }: PipelineStepperProps) {
  const isVertical = orientation === "vertical";

  return (
    <div className={cn(
      "flex gap-0",
      isVertical ? "flex-col" : "flex-row overflow-x-auto no-scrollbar",
      className
    )}>
      {steps.map((step, i) => (
        <div key={step.id} className={cn(
          "flex items-center",
          isVertical ? "flex-row" : "flex-col",
          !isVertical && "min-w-[100px] flex-1"
        )}>
          <div className={cn("flex items-center", isVertical ? "flex-col mr-3" : "flex-row w-full")}>
            {i > 0 && (
              <div className={cn(
                isVertical ? "w-0.5 h-6" : "h-0.5 flex-1",
                step.status === "completed" || step.status === "active"
                  ? "bg-primary"
                  : "bg-border"
              )} />
            )}
            <motion.div
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              className={cn(
                "rounded-full flex items-center justify-center shrink-0 transition-all",
                step.status === "completed" && "bg-primary text-primary-foreground h-7 w-7",
                step.status === "active" && "bg-primary/20 border-2 border-primary text-primary h-8 w-8 glow",
                step.status === "upcoming" && "bg-muted border border-border text-muted-foreground h-7 w-7",
                step.status === "skipped" && "bg-muted/50 text-muted-foreground/50 h-7 w-7",
              )}
            >
              {step.status === "completed" ? (
                <Check className="h-3.5 w-3.5" />
              ) : step.status === "active" ? (
                <Circle className="h-3 w-3 fill-current" />
              ) : (
                <Clock className="h-3.5 w-3.5" />
              )}
            </motion.div>
            {i < steps.length - 1 && (
              <div className={cn(
                isVertical ? "w-0.5 h-6" : "h-0.5 flex-1",
                steps[i + 1].status === "completed" || steps[i + 1].status === "active"
                  ? "bg-primary"
                  : "bg-border"
              )} />
            )}
          </div>
          <div className={cn(
            "text-center",
            isVertical ? "py-1" : "mt-2 px-1"
          )}>
            <p className={cn(
              "text-xs font-medium leading-tight",
              step.status === "active" && "text-primary",
              step.status === "completed" && "text-foreground",
              step.status === "upcoming" && "text-muted-foreground",
              step.status === "skipped" && "text-muted-foreground/50",
            )}>
              {step.name}
            </p>
            {step.completionPct !== undefined && step.status === "active" && (
              <p className="text-[10px] text-primary mt-0.5">{step.completionPct}%</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
