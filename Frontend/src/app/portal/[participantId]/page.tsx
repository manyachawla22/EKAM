"use client";
import { use } from "react";
import { mockParticipants, mockEvents } from "@/lib/mock-data";
import { ApprovalBadge } from "@/components/approval-badge";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { motion } from "framer-motion";
import { toast } from "sonner";
import Link from "next/link";
import {
  Zap, Users, Calendar, CheckCircle2, Clock, FileText, Bell,
  ArrowRight, Star, Trophy, Activity, Sun, Moon
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { ThemeToggle } from "@/components/theme-toggle";

export default function ParticipantPortal({ params }: { params: Promise<{ participantId: string }> }) {
  const { participantId } = use(params);
  const { theme, toggleTheme } = useAppStore();
  const participant = mockParticipants.find((p) => p.id === participantId) || mockParticipants[0];
  const event = mockEvents[0];
  const teamMembers = mockParticipants.filter((p) => p.team === participant.team);

  const timeline = [
    { date: "Apr 15", title: "Registration Confirmed", desc: "You've been registered for HackSphere 2026", status: "completed" as const },
    { date: "Apr 25", title: "Resume Screening Passed", desc: `ATS Score: ${participant.atsScore}/100`, status: "completed" as const },
    { date: "May 01", title: "Online Assessment Complete", desc: "Scored in top 68% of applicants", status: "completed" as const },
    { date: "May 05", title: `Joined Team ${participant.team}`, desc: `Team of ${teamMembers.length} members formed`, status: "completed" as const },
    { date: "May 17", title: "Hackathon Started", desc: "48-hour sprint begins!", status: "active" as const },
    { date: "May 19", title: "Submission Deadline", desc: "Submit your project by 4:00 PM", status: "upcoming" as const },
    { date: "May 20", title: "Results Announcement", desc: "Winners announced live", status: "upcoming" as const },
  ];

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto flex items-center justify-between h-14 px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold">Ekam</span>
          </Link>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px]">Participant Portal</Badge>
            <ThemeToggle />
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Profile Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm overflow-hidden">
            <div className="h-24 bg-muted/30" />
            <CardContent className="p-6 -mt-12">
              <div className="flex flex-col sm:flex-row items-start gap-4">
                <Avatar className="h-20 w-20 border-4 border-card">
                  <AvatarFallback className="bg-primary/10 text-primary text-xl font-bold">
                    {participant.name.split(" ").map((n) => n[0]).join("")}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <h1 className="text-2xl font-bold">{participant.name}</h1>
                  <p className="text-sm text-muted-foreground">{participant.email}</p>
                  <div className="flex items-center gap-3 mt-2 flex-wrap">
                    <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">{participant.institution}</Badge>
                    <ApprovalBadge status={participant.registrationStatus === "confirmed" ? "approved" : "pending"} />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Current Event */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Current Event</CardTitle>
                <ApprovalBadge status="in_progress" />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold">{event.name}</h3>
                <p className="text-sm text-muted-foreground">{event.description}</p>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "Stage", value: event.stage, icon: Activity },
                  { label: "Progress", value: `${event.progress}%`, icon: Trophy },
                  { label: "Teams", value: event.teamCount, icon: Users },
                  { label: "Days Left", value: "1", icon: Calendar },
                ].map((s) => (
                  <div key={s.label} className="text-center p-3 rounded-xl bg-muted/20 border border-border/30">
                    <s.icon className="h-4 w-4 mx-auto mb-1.5 text-primary" />
                    <p className="text-lg font-bold">{s.value}</p>
                    <p className="text-[10px] text-muted-foreground">{s.label}</p>
                  </div>
                ))}
              </div>
              <PipelineStepper
                steps={event.stages.slice(0, 6).map((s) => ({ id: s.id, name: s.name, status: s.status, completionPct: s.completionPct }))}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Team + Key Dates */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Team */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm h-full">
              <CardHeader><CardTitle className="text-base">Your Team — {participant.team}</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {teamMembers.map((m) => (
                  <div key={m.id} className="flex items-center gap-3 py-2 border-b border-border/20 last:border-0">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback className="bg-primary/10 text-primary text-xs">{m.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{m.name}{m.id === participant.id ? " (You)" : ""}</p>
                      <p className="text-xs text-muted-foreground">{m.institution}</p>
                    </div>
                    <div className="flex gap-1">
                      {m.skills.slice(0, 2).map((s) => <Badge key={s} variant="outline" className="text-[9px] px-1.5 py-0">{s}</Badge>)}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>

          {/* Key Dates */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm h-full">
              <CardHeader><CardTitle className="text-base">Key Dates</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {[
                  { date: "May 17", event: "Hackathon Begins", status: "Completed" },
                  { date: "May 18", event: "Mentor Sessions", status: "In Progress" },
                  { date: "May 19, 4 PM", event: "Submission Deadline", status: "Upcoming" },
                  { date: "May 20", event: "Results Day", status: "Upcoming" },
                ].map((d) => (
                  <div key={d.event} className="flex items-center justify-between py-2 border-b border-border/20 last:border-0">
                    <div>
                      <p className="text-sm font-medium">{d.event}</p>
                      <p className="text-xs text-muted-foreground">{d.date}</p>
                    </div>
                    <ApprovalBadge status={d.status === "Completed" ? "completed" : d.status === "In Progress" ? "in_progress" : "pending"} />
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Submission Status */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm border-primary/20">
            <CardHeader>
              <CardTitle className="text-base">Submission Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
                <Clock className="h-5 w-5 text-amber-500" />
                <div>
                  <p className="text-sm font-medium">Submission window opens in 6 hours</p>
                  <p className="text-xs text-muted-foreground">Deadline: May 19, 2026 at 4:00 PM IST</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <Button variant="outline" className="text-xs"><FileText className="h-3.5 w-3.5 mr-1" />Upload Files</Button>
                <Button variant="outline" className="text-xs"><Star className="h-3.5 w-3.5 mr-1" />Add Demo Link</Button>
                <Button className="text-xs bg-primary hover:bg-primary/90" onClick={() => toast.info("Submission window not yet open")}>
                  Submit Project
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Activity Timeline */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader><CardTitle className="text-base">Activity Timeline</CardTitle></CardHeader>
            <CardContent>
              <div className="relative">
                <div className="absolute left-3.5 top-0 bottom-0 w-px bg-border" />
                <div className="space-y-6">
                  {timeline.map((t, i) => (
                    <div key={i} className="flex gap-4 relative">
                      <div className={`z-10 rounded-full h-7 w-7 flex items-center justify-center shrink-0 ${
                        t.status === "completed" ? "bg-primary text-primary-foreground" :
                        t.status === "active" ? "bg-primary/20 border-2 border-primary text-primary" :
                        "bg-muted border border-border text-muted-foreground"
                      }`}>
                        {t.status === "completed" ? <CheckCircle2 className="h-3.5 w-3.5" /> :
                         t.status === "active" ? <Activity className="h-3.5 w-3.5" /> :
                         <Clock className="h-3.5 w-3.5" />}
                      </div>
                      <div className="pb-2">
                        <p className="text-xs text-muted-foreground">{t.date}</p>
                        <p className="text-sm font-medium">{t.title}</p>
                        <p className="text-xs text-muted-foreground">{t.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Notices */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader><CardTitle className="text-base flex items-center gap-2"><Bell className="h-4 w-4" />Announcements</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {[
                { title: "Submission Guidelines Updated", desc: "Please include a README.md in your project repository. Video demos are now mandatory.", time: "1 hour ago", urgent: true },
                { title: "Mentor Office Hours Available", desc: "Book a 15-min session with industry mentors via the scheduler.", time: "3 hours ago", urgent: false },
                { title: "API Endpoint for Testing", desc: "Use the sandbox API at sandbox.ekam.io for testing. Rate limit: 100 req/min.", time: "Yesterday", urgent: false },
              ].map((n, i) => (
                <div key={i} className={`p-3 rounded-xl border ${n.urgent ? "border-amber-500/20 bg-amber-500/5" : "border-border/30 bg-muted/10"}`}>
                  <div className="flex items-center gap-2">
                    {n.urgent && <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[9px]">Important</Badge>}
                    <p className="text-sm font-medium">{n.title}</p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{n.desc}</p>
                  <p className="text-[10px] text-muted-foreground mt-1.5">{n.time}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
