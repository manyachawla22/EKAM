"use client";
import { use } from "react";
import { mockEvents, mockParticipants, mockJudges, mockSubmissions } from "@/lib/mock-data";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { ApprovalBadge } from "@/components/approval-badge";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { motion } from "framer-motion";
import { toast } from "sonner";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  Users, Gavel, Calendar, Hash, ArrowRight, Clock, Mail, AlertTriangle,
  FileText, CheckCircle2, Play, Eye, Send, BarChart3, Trophy,
  MessageSquare, Globe, Layers, Clipboard, UserCheck, Sparkles, Activity
} from "lucide-react";

export default function EventDetailPage({ params }: { params: Promise<{ hash: string }> }) {
  const { hash } = use(params);
  const event = mockEvents.find((e) => e.hash === hash) || mockEvents[0];
  const eventParticipants = mockParticipants.slice(0, event.participantCount > 20 ? 20 : event.participantCount);
  const eventJudges = mockJudges.filter((j) => j.assignedEvents.includes(event.hash));
  const eventSubs = mockSubmissions.filter((s) => s.eventHash === event.hash);

  const workflowStages = [
    { name: "Registration", status: "completed" as const, owner: "Organizer", count: `${event.participantCount}/${event.maxParticipants}`, pct: Math.round((event.participantCount / event.maxParticipants) * 100), lastUpdated: "2026-04-20", actions: ["View Registrations"] },
    { name: "Resume Screening", status: "completed" as const, owner: "System", count: "400 screened", pct: 100, lastUpdated: "2026-04-25", actions: ["View ATS Scores"] },
    { name: "Online Assessment", status: "completed" as const, owner: "System", count: "342 passed", pct: 100, lastUpdated: "2026-05-01", actions: ["View Results"] },
    { name: "Team Formation", status: "completed" as const, owner: "Participant", count: `${event.teamCount} teams`, pct: 100, lastUpdated: "2026-05-05", actions: ["View Teams"] },
    { name: "Theme Selection", status: "completed" as const, owner: "Organizer", count: "8 themes", pct: 100, lastUpdated: "2026-05-08", actions: ["View Themes"] },
    { name: "Hacking Phase", status: "active" as const, owner: "Participant", count: "45% complete", pct: 45, lastUpdated: "2026-05-18", actions: ["Monitor Progress"] },
    { name: "Submission", status: "upcoming" as const, owner: "Participant", count: "0 submitted", pct: 0, lastUpdated: "-", actions: ["Configure"] },
    { name: "Judging", status: "upcoming" as const, owner: "Judge", count: "0 reviewed", pct: 0, lastUpdated: "-", actions: ["Assign Judges"] },
    { name: "Results", status: "upcoming" as const, owner: "Organizer", count: "-", pct: 0, lastUpdated: "-", actions: ["Configure"] },
  ];

  const statusColors: Record<string, string> = {
    completed: "bg-emerald-500/10 text-emerald-500",
    active: "bg-blue-500/10 text-blue-500",
    upcoming: "bg-muted text-muted-foreground",
  };

  return (
    <div className="min-h-screen">
      {/* Top nav */}
      <nav className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto flex items-center justify-between h-14 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" render={<Link href="/dashboard" />}>← Dashboard</Button>
            <span className="text-muted-foreground">/</span>
            <span className="text-sm font-medium">{event.name}</span>
            <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hidden sm:inline-flex">{event.status}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="outline" size="sm" onClick={() => toast.info("Sharing event link...")}><Send className="h-3.5 w-3.5 mr-1.5" />Share</Button>
            <Button size="sm" className="bg-primary hover:bg-primary/90"><Play className="h-3.5 w-3.5 mr-1.5" />Next Action</Button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Header stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <StatCard title="Participants" value={event.participantCount} icon={Users} />
          <StatCard title="Teams" value={event.teamCount} icon={Users} />
          <StatCard title="Judges" value={event.judgeCount} icon={Gavel} />
          <StatCard title="Submissions" value={eventSubs.length} icon={FileText} />
          <StatCard title="Progress" value={`${event.progress}%`} icon={Activity} />
          <StatCard title="Anomalies" value="1" icon={AlertTriangle} />
        </div>

        {/* Pipeline */}
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Event Pipeline</CardTitle>
          </CardHeader>
          <CardContent>
            <PipelineStepper steps={event.stages.map((s) => ({ id: s.id, name: s.name, status: s.status, completionPct: s.completionPct }))} />
          </CardContent>
        </Card>

        {/* Main content tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="flex-wrap h-auto gap-1 bg-transparent p-0">
            {["overview", "workflow", "teams", "judges", "submissions", "rounds", "comms"].map((t) => (
              <TabsTrigger key={t} value={t} className="capitalize data-[state=active]:bg-primary/10 data-[state=active]:text-primary rounded-lg px-3 py-1.5 text-xs">
                {t}
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <Card className="lg:col-span-2 border-border/50 bg-card/80 backdrop-blur-sm">
                <CardHeader><CardTitle className="text-base">Event Overview</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">{event.description}</p>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div><span className="text-muted-foreground">Type:</span> <span className="font-medium ml-1">{event.type}</span></div>
                    <div><span className="text-muted-foreground">Hash:</span> <span className="font-mono font-medium ml-1">{event.hash}</span></div>
                    <div><span className="text-muted-foreground">Created:</span> <span className="font-medium ml-1">{event.createdAt}</span></div>
                    <div><span className="text-muted-foreground">Updated:</span> <span className="font-medium ml-1">{event.updatedAt}</span></div>
                  </div>
                </CardContent>
              </Card>
              {/* Sticky panel */}
              <Card className="border-border/50 bg-card/80 backdrop-blur-sm border-primary/20">
                <CardHeader><CardTitle className="text-base">Quick Status</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  {[
                    { label: "Current Stage", value: event.stage, icon: Activity, color: "text-primary" },
                    { label: "Next Action", value: "Collect Submissions", icon: ArrowRight, color: "text-amber-500" },
                    { label: "Pending Approvals", value: "0", icon: Clock, color: "text-emerald-500" },
                    { label: "Comms Status", value: "342 emails sent", icon: Mail, color: "text-blue-500" },
                    { label: "Anomalies", value: "1 flagged", icon: AlertTriangle, color: "text-red-400" },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between py-1">
                      <div className="flex items-center gap-2"><item.icon className={`h-3.5 w-3.5 ${item.color}`} /><span className="text-xs text-muted-foreground">{item.label}</span></div>
                      <span className="text-xs font-medium">{item.value}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
            {/* Schedule / Meetups */}
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
              <CardHeader><CardTitle className="text-base">Schedule & Meetups</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { title: "Opening Ceremony", date: "May 17, 10:00 AM", status: "Completed" },
                    { title: "Mentor Office Hours", date: "May 18, 2:00 PM", status: "In Progress" },
                    { title: "Final Presentations", date: "May 19, 4:00 PM", status: "Upcoming" },
                  ].map((m) => (
                    <div key={m.title} className="p-3 rounded-xl border border-border/30 bg-muted/20">
                      <p className="text-sm font-medium">{m.title}</p>
                      <p className="text-xs text-muted-foreground mt-1">{m.date}</p>
                      <ApprovalBadge status={m.status === "Completed" ? "completed" : m.status === "In Progress" ? "in_progress" : "pending"} className="mt-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Workflow Tab */}
          <TabsContent value="workflow" className="space-y-3">
            {workflowStages.map((ws, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                  <CardContent className="p-4 flex flex-col sm:flex-row items-start sm:items-center gap-4">
                    <div className={`rounded-lg p-2 ${statusColors[ws.status]}`}>
                      {ws.status === "completed" ? <CheckCircle2 className="h-4 w-4" /> : ws.status === "active" ? <Play className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-sm">{ws.name}</p>
                        <ApprovalBadge status={ws.status === "completed" ? "completed" : ws.status === "active" ? "in_progress" : "pending"} />
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                        <span>Owner: {ws.owner}</span>
                        <span>{ws.count}</span>
                        <span>Updated: {ws.lastUpdated}</span>
                      </div>
                      <Progress value={ws.pct} className="h-1 mt-2 max-w-xs" />
                    </div>
                    <div className="flex gap-2">
                      {ws.actions.map((a) => (
                        <Button key={a} variant="outline" size="sm" className="text-xs" onClick={() => toast.info(`Action: ${a}`)}>
                          {a}
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </TabsContent>

          {/* Teams Tab */}
          <TabsContent value="teams">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {["ByteForce", "Neural Ninjas", "CodeCrafters", "DataDragons", "PixelPioneers", "QuantumLeap"].map((team, i) => {
                const members = mockParticipants.filter((p) => p.team === team);
                return (
                  <motion.div key={team} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                    <Card className="border-border/50 bg-card/80 backdrop-blur-sm hover:border-primary/20 transition-all">
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <p className="font-semibold text-sm">{team}</p>
                          <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-500 border-emerald-500/20">Active</Badge>
                        </div>
                        <div className="flex -space-x-2 mb-3">
                          {members.map((m) => (
                            <Avatar key={m.id} className="h-7 w-7 border-2 border-card">
                              <AvatarFallback className="text-[9px] bg-primary/10 text-primary">{m.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback>
                            </Avatar>
                          ))}
                          {members.length === 0 && <span className="text-xs text-muted-foreground">3 members</span>}
                        </div>
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{members.length || 3} members</span>
                          <span>Theme: AI/ML</span>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          </TabsContent>

          {/* Judges Tab */}
          <TabsContent value="judges">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {eventJudges.length > 0 ? eventJudges.map((j, i) => (
                <motion.div key={j.id} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                  <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3 mb-3">
                        <Avatar className="h-10 w-10"><AvatarFallback className="bg-primary/10 text-primary">{j.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback></Avatar>
                        <div>
                          <p className="font-semibold text-sm">{j.name}</p>
                          <p className="text-xs text-muted-foreground">{j.institution}</p>
                        </div>
                      </div>
                      <div className="flex gap-1 flex-wrap mb-3">
                        {j.expertise.map((e) => <Badge key={e} variant="outline" className="text-[9px]">{e}</Badge>)}
                      </div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Rating: {j.rating}/5.0</span>
                        <span>{j.email}</span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              )) : mockJudges.map((j, i) => (
                <motion.div key={j.id} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                  <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3 mb-3">
                        <Avatar className="h-10 w-10"><AvatarFallback className="bg-primary/10 text-primary">{j.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback></Avatar>
                        <div><p className="font-semibold text-sm">{j.name}</p><p className="text-xs text-muted-foreground">{j.institution}</p></div>
                      </div>
                      <div className="flex gap-1 flex-wrap mb-3">{j.expertise.map((e) => <Badge key={e} variant="outline" className="text-[9px]">{e}</Badge>)}</div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground"><span>Rating: {j.rating}/5.0</span></div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </TabsContent>

          {/* Submissions Tab */}
          <TabsContent value="submissions">
            <div className="space-y-3">
              {eventSubs.map((sub, i) => (
                <motion.div key={sub.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                  <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="p-4 flex flex-col sm:flex-row items-start sm:items-center gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-sm">{sub.teamName}</p>
                          <ApprovalBadge status={sub.status === "reviewed" ? "completed" : sub.status === "flagged" ? "flagged" : sub.status === "finalised" ? "approved" : "pending"} />
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                          <span>Round: {sub.round}</span>
                          <span>Submitted: {new Date(sub.submittedAt).toLocaleString()}</span>
                          <span>{sub.attachments.length} files</span>
                        </div>
                        {sub.feedback && <p className="text-xs mt-2 text-muted-foreground italic">&quot;{sub.feedback}&quot;</p>}
                      </div>
                      <div className="flex items-center gap-4">
                        {sub.score !== null && (
                          <div className="text-center">
                            <p className="text-lg font-bold">{sub.score}</p>
                            <p className="text-[10px] text-muted-foreground">Score</p>
                          </div>
                        )}
                        {sub.panelAvg !== null && (
                          <div className="text-center">
                            <p className="text-lg font-bold text-muted-foreground">{sub.panelAvg}</p>
                            <p className="text-[10px] text-muted-foreground">Panel Avg</p>
                          </div>
                        )}
                        <Button variant="outline" size="sm" onClick={() => toast.info("Opening submission details...")}><Eye className="h-3.5 w-3.5" /></Button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </TabsContent>

          {/* Rounds Tab */}
          <TabsContent value="rounds">
            <div className="space-y-4">
              {event.rounds.map((round, i) => (
                <Card key={round.id} className="border-border/50 bg-card/80 backdrop-blur-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold">{round.name}</p>
                        <ApprovalBadge status={round.status === "completed" ? "completed" : round.status === "active" ? "in_progress" : "pending"} />
                      </div>
                      <span className="text-xs text-muted-foreground">{round.startDate} → {round.endDate}</span>
                    </div>
                    <div className="flex items-center gap-6 text-sm">
                      <span className="text-muted-foreground">Advanced: <span className="font-medium text-foreground">{round.participantsAdvanced}</span></span>
                      <span className="text-muted-foreground">Total: <span className="font-medium text-foreground">{round.totalParticipants}</span></span>
                      {round.totalParticipants > 0 && (
                        <span className="text-muted-foreground">Rate: <span className="font-medium text-foreground">{Math.round((round.participantsAdvanced / round.totalParticipants) * 100)}%</span></span>
                      )}
                    </div>
                    {round.totalParticipants > 0 && <Progress value={(round.participantsAdvanced / round.totalParticipants) * 100} className="h-1.5 mt-3" />}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Comms Tab */}
          <TabsContent value="comms">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { platform: "Email", icon: Mail, count: "342 sent", status: "Active", lastSent: "2 hours ago", desc: "Automated round reminders and updates" },
                { platform: "WhatsApp", icon: MessageSquare, count: "68 groups", status: "Active", lastSent: "1 hour ago", desc: "Team coordination and announcements" },
                { platform: "Discord", icon: Globe, count: "1 server", status: "Active", lastSent: "30 min ago", desc: "Real-time participant support channel" },
              ].map((c) => (
                <Card key={c.platform} className="border-border/50 bg-card/80 backdrop-blur-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="rounded-lg bg-primary/10 p-2"><c.icon className="h-4 w-4 text-primary" /></div>
                      <div><p className="font-semibold text-sm">{c.platform}</p><p className="text-xs text-muted-foreground">{c.desc}</p></div>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">{c.count} • Last: {c.lastSent}</span>
                      <ApprovalBadge status="approved" />
                    </div>
                  </CardContent>
                </Card>
              ))}
              <Card className="border-border/50 bg-card/80 backdrop-blur-sm border-dashed">
                <CardContent className="p-4 flex items-center justify-center h-full">
                  <Button variant="ghost" className="text-muted-foreground" onClick={() => toast.info("Adding integration...")}><Sparkles className="h-4 w-4 mr-2" />Add Integration</Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
