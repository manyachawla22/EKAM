"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Calendar, Users, Gavel, ArrowRight, Hash } from "lucide-react";
import { motion } from "framer-motion";
import type { Event } from "@/lib/mock-data";
import Link from "next/link";

interface EventCardProps {
  event: Event;
  index?: number;
}

const statusColors: Record<string, string> = {
  active: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  draft: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  completed: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  archived: "bg-muted text-muted-foreground border-muted",
};

const approvalColors: Record<string, string> = {
  approved: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  pending: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  rejected: "bg-red-500/10 text-red-500 border-red-500/20",
};

export function EventCard({ event, index = 0 }: EventCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
      whileHover={{ y: -3 }}
    >
      <Card className="group relative overflow-hidden border-border/50 bg-card/80 backdrop-blur-sm hover:border-primary/30 transition-all duration-300">
        <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity" />
        <CardHeader className="pb-3 relative">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <CardTitle className="text-lg font-semibold truncate">{event.name}</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <Hash className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-mono">{event.hash}</span>
                <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0", statusColors[event.status])}>
                  {event.status}
                </Badge>
              </div>
            </div>
            <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0 shrink-0", approvalColors[event.approvalStatus])}>
              {event.approvalStatus}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="relative space-y-4">
          <p className="text-sm text-muted-foreground line-clamp-2">{event.description}</p>

          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><Users className="h-3.5 w-3.5" />{event.participantCount}</span>
            <span className="flex items-center gap-1"><Gavel className="h-3.5 w-3.5" />{event.judgeCount}</span>
            <span className="flex items-center gap-1"><Calendar className="h-3.5 w-3.5" />{event.updatedAt}</span>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Stage: {event.stage}</span>
              <span className="font-medium">{event.progress}%</span>
            </div>
            <Progress value={event.progress} className="h-1.5" />
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-muted-foreground">{event.type}</span>
            <Button variant="ghost" size="sm" render={<Link href={`/event/${event.hash}`} />} className="group/btn">
              View Details
              <ArrowRight className="ml-1 h-3.5 w-3.5 transition-transform group-hover/btn:translate-x-0.5" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
