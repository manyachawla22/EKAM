"use client";
import { StatCard } from "@/components/stat-card";
import { EventCard } from "@/components/event-card";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { mockEvents, mockActivities } from "@/lib/mock-data";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Calendar, Users, Clock, Gavel, FileText, CheckCircle2, Plus,
  Activity, ArrowRight, AlertTriangle, Mail, UserCheck
} from "lucide-react";

const activityIcons: Record<string, React.ElementType> = {
  participant: Users, judge: Gavel, communication: Mail, system: AlertTriangle, event: Calendar,
};
const activityColors: Record<string, string> = {
  participant: "text-emerald-500 bg-emerald-500/10",
  judge: "text-amber-500 bg-amber-500/10",
  communication: "text-blue-500 bg-blue-500/10",
  system: "text-red-400 bg-red-400/10",
  event: "text-primary bg-primary/10",
};

export default function DashboardPage() {
  const activeEvent = mockEvents.find((e) => e.status === "active");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Welcome back! Here&apos;s your event overview.</p>
        </div>
        <Button render={<Link href="/dashboard/create" />} className="bg-primary hover:bg-primary/90">
          <Plus className="h-4 w-4 mr-2" />Create New Event
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard title="Total Events" value={mockEvents.length} icon={Calendar} trend={{ value: 12, positive: true }} gradient="bg-primary/10" />
        <StatCard title="Active Events" value={mockEvents.filter((e) => e.status === "active").length} icon={Activity} />
        <StatCard title="Pending Approvals" value={1} icon={Clock} trend={{ value: 5, positive: false }} />
        <StatCard title="Participants" value="522" icon={Users} trend={{ value: 18, positive: true }} />
        <StatCard title="Judges Assigned" value="25" icon={Gavel} />
        <StatCard title="Reports Generated" value="12" icon={FileText} trend={{ value: 8, positive: true }} />
      </div>

      {/* Pipeline + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline */}
        <Card className="lg:col-span-2 border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Event Pipeline — {activeEvent?.name}</CardTitle>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px]">Active</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {activeEvent && (
              <PipelineStepper
                steps={activeEvent.stages.map((s) => ({
                  id: s.id, name: s.name, status: s.status, completionPct: s.completionPct,
                }))}
              />
            )}
          </CardContent>
        </Card>

        {/* Status Overview */}
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Status Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: "Current Stage", value: activeEvent?.stage || "-", icon: Activity, color: "text-primary" },
              { label: "Next Action", value: "Collect Submissions", icon: ArrowRight, color: "text-amber-500" },
              { label: "Pending Approvals", value: "1 event draft", icon: Clock, color: "text-orange-500" },
              { label: "Communications", value: "342 emails sent", icon: Mail, color: "text-blue-500" },
              { label: "Anomalies", value: "1 score flagged", icon: AlertTriangle, color: "text-red-400" },
              { label: "Teams Confirmed", value: "68 / 70", icon: UserCheck, color: "text-emerald-500" },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between py-1.5">
                <div className="flex items-center gap-2">
                  <item.icon className={`h-3.5 w-3.5 ${item.color}`} />
                  <span className="text-xs text-muted-foreground">{item.label}</span>
                </div>
                <span className="text-xs font-medium">{item.value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Events + Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Events */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Your Events</h2>
            <Button variant="ghost" size="sm" render={<Link href="/dashboard/events" />}>
              View All <ArrowRight className="ml-1 h-3.5 w-3.5" />
            </Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {mockEvents.map((event, i) => (
              <EventCard key={event.id} event={event} index={i} />
            ))}
          </div>
        </div>

        {/* Activity Feed */}
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[400px]">
              <div className="px-6 pb-4 space-y-1">
                {mockActivities.map((a, i) => {
                  const Icon = activityIcons[a.type] || Activity;
                  return (
                    <motion.div
                      key={a.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex gap-3 py-3 border-b border-border/30 last:border-0"
                    >
                      <div className={`rounded-lg p-1.5 h-7 w-7 flex items-center justify-center shrink-0 ${activityColors[a.type]}`}>
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs leading-relaxed">{a.action}</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5">{a.timestamp}</p>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
