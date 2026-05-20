"use client";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: { value: number; positive: boolean };
  className?: string;
  gradient?: string;
}

export function StatCard({ title, value, subtitle, icon: Icon, trend, className, gradient }: StatCardProps) {
  return (
    <motion.div whileHover={{ y: -2, scale: 1.01 }} transition={{ duration: 0.2 }}>
      <Card className={cn("relative overflow-hidden border-border/50 bg-card/80 backdrop-blur-sm", className)}>
        {gradient && (
          <div className={cn("absolute inset-0 opacity-10", gradient)} />
        )}
        <CardContent className="p-5 relative">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground font-medium">{title}</p>
              <p className="text-2xl font-bold tracking-tight">{value}</p>
              {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
              {trend && (
                <p className={cn("text-xs font-medium", trend.positive ? "text-emerald-500" : "text-red-400")}>
                  {trend.positive ? "↑" : "↓"} {Math.abs(trend.value)}% from last week
                </p>
              )}
            </div>
            <div className="rounded-xl bg-primary/10 p-2.5">
              <Icon className="h-5 w-5 text-primary" />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
