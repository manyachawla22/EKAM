"use client";
import { use, useState, useEffect } from "react";
import { mockEvents, mockParticipants, mockJudges, mockSubmissions } from "@/lib/mock-data";
import { mapApiConfigToEvent } from "@/app/dashboard/events/page";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { ApprovalBadge } from "@/components/approval-badge";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { motion } from "framer-motion";
import { toast } from "sonner";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import { aiApi } from "@/lib/api";
import {
  Users, Gavel, FileText, AlertTriangle,
  CheckCircle2, Play, Eye, Send, Trophy,
  MessageSquare, Globe, Mail, Clock, ArrowRight,
  Activity, Sparkles,
} from "lucide-react";

export default function EventDetailPage({ params }: { params: Promise<{ hash: string }> }) {
  const { hash } = use(params);

  const [apiEvent, setApiEvent] = useState<Record<string, any> | null>(null);
  const [loadingApi, setLoadingApi] = useState(true);

  useEffect(() => {
    aiApi.getEventByHash(hash)
      .then((data: Record<string, any>) => setApiEvent(data))
      .catch(() => {})
      .finally(() => setLoadingApi(false));
  }, [hash]);

  // Prefer live API data; fall back to mock for demo events
  const mockEvent = mockEvents.find((e) => e.hash === hash) || mockEvents[0];
  const event = apiEvent ? mapApiConfigToEvent(apiEvent) : mockEvent;

  const eventParticipants = mockParticipants.slice(0, Math.min(event.participantCount || 6, 20));
  const eventJudges = mockJudges.filter((j) => j.assignedEvents.includes(event.hash));
  const eventSubs = mockSubmissions.filter((s) => s.eventHash === event.hash);

  // ── Derived from API config when available ─────────────────────────────────
  const venue = apiEvent?.core?.venue;
  const contact = apiEvent?.core?.contact;
  const prizes = apiEvent?.prizes;
  const keyDates: { name: string; date: string; description: string }[] =
    apiEvent?.timeline?.key_dates || [];
  const regOpens = apiEvent?.timeline?.registration?.opens_at;
  const regCloses = apiEvent?.timeline?.registration?.closes_at;
  const apiJudges: any[] = apiEvent?.judging_panel?.judges || [];
  const apiRounds: any[] = apiEvent?.rounds || [];
  const theme = apiEvent?.core?.theme || "";
  const mode = apiEvent?.core?.mode || "";

  const workflowStages = [
    { name: "Registration", status: "upcoming" as const, owner: "Organizer", count: `0/${event.maxParticipants || "?"}`, pct: 0, lastUpdated: regOpens?.slice(0, 10) || "-", actions: ["View Registrations"] },
    ...apiRounds.map((r: any) => ({
      name: r.round_name || "Round",
      status: "upcoming" as const,
      owner: "Participant",
      count: "Not started",
      pct: 0,
      lastUpdated: r.dates?.starts_at?.slice(0, 10) || "-",
      actions: ["View Details"],
    })),
    { name: "Results", status: "upcoming" as const, owner: "Organizer", count: "-", pct: 0, lastUpdated: "-", actions: ["Configure"] },
  ];

  const statusColors: Record<string, string> = {
    completed: "bg-emerald-500/10 text-emerald-500",
    active: "bg-blue-500/10 text-blue-500",
    upcoming: "bg-muted text-muted-foreground",
  };

  if (loadingApi) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />
          ))}
        </div>
      </div>
    );
  }

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
          <StatCard title="Teams" value={event.teamCount || event.maxParticipants ? `0/${apiEvent?.participants?.capacity?.max_teams || "?"}` : 0} icon={Users} />
          <StatCard title="Judges" value={apiJudges.length || event.judgeCount} icon={Gavel} />
          <StatCard title="Rounds" value={apiRounds.length || event.rounds.length} icon={FileText} />
          <StatCard title="Progress" value={`${event.progress}%`} icon={Activity} />
          <StatCard title="Prize Pool" value={prizes?.total_pool || "—"} icon={Trophy} />
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

        {/* Tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="flex-wrap h-auto gap-1 bg-transparent p-0">
            {["overview", "workflow", "rounds", "judges", "prizes", "teams", "submissions", "comms"].map((t) => (
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
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    <div><span className="text-muted-foreground">Type:</span> <span className="font-medium ml-1">{event.type}</span></div>
                    <div><span className="text-muted-foreground">Hash:</span> <span className="font-mono font-medium ml-1">{event.hash}</span></div>
                    {theme && <div><span className="text-muted-foreground">Theme:</span> <span className="font-medium ml-1">{theme}</span></div>}
                    {mode && <div><span className="text-muted-foreground">Mode:</span> <span className="font-medium ml-1 capitalize">{mode}</span></div>}
                    <div><span className="text-muted-foreground">Created:</span> <span className="font-medium ml-1">{event.createdAt}</span></div>
                    <div><span className="text-muted-foreground">Updated:</span> <span className="font-medium ml-1">{event.updatedAt}</span></div>
                    {venue?.city && <div><span className="text-muted-foreground">Venue:</span> <span className="font-medium ml-1">{[venue.name, venue.city, venue.country].filter(Boolean).join(", ")}</span></div>}
                    {contact?.email && <div><span className="text-muted-foreground">Contact:</span> <span className="font-medium ml-1">{contact.email}</span></div>}
                    {contact?.phone && <div><span className="text-muted-foreground">Phone:</span> <span className="font-medium ml-1">{contact.phone}</span></div>}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50 bg-card/80 backdrop-blur-sm border-primary/20">
                <CardHeader><CardTitle className="text-base">Quick Status</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  {[
                    { label: "Current Phase", value: event.stage, icon: Activity, color: "text-primary" },
                    { label: "Registration Opens", value: regOpens?.slice(0, 10) || "—", icon: Clock, color: "text-emerald-500" },
                    { label: "Registration Closes", value: regCloses?.slice(0, 10) || "—", icon: Clock, color: "text-amber-500" },
                    { label: "Max Teams", value: apiEvent?.participants?.capacity?.max_teams ?? "—", icon: Users, color: "text-blue-500" },
                    { label: "Team Size", value: apiEvent?.participants?.team ? `${apiEvent.participants.team.min_size}–${apiEvent.participants.team.max_size}` : "—", icon: Users, color: "text-violet-500" },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between py-1">
                      <div className="flex items-center gap-2"><item.icon className={`h-3.5 w-3.5 ${item.color}`} /><span className="text-xs text-muted-foreground">{item.label}</span></div>
                      <span className="text-xs font-medium">{String(item.value)}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            {/* Key dates */}
            {keyDates.length > 0 && (
              <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                <CardHeader><CardTitle className="text-base">Key Dates</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {keyDates.map((d) => (
                      <div key={d.name} className="p-3 rounded-xl border border-border/30 bg-muted/20">
                        <p className="text-sm font-medium">{d.name}</p>
                        <p className="text-xs text-muted-foreground mt-1">{d.date?.slice(0, 16).replace("T", " ")}</p>
                        {d.description && <p className="text-xs text-muted-foreground/70 mt-0.5">{d.description}</p>}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
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
                        <Button key={a} variant="outline" size="sm" className="text-xs" onClick={() => toast.info(`Action: ${a}`)}>{a}</Button>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </TabsContent>

          {/* Rounds Tab */}
          <TabsContent value="rounds">
            <div className="space-y-4">
              {(apiRounds.length > 0 ? apiRounds : event.rounds).map((round: any, i: number) => {
                const isApi = apiRounds.length > 0;
                const name = isApi ? round.round_name : round.name;
                const startDate = isApi ? round.dates?.starts_at?.slice(0, 10) : round.startDate;
                const endDate = isApi ? round.dates?.ends_at?.slice(0, 10) : round.endDate;
                const criteria: any[] = isApi ? (round.scoring?.criteria || []) : [];
                return (
                  <Card key={round.round_id || round.id || i} className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold">{name}</p>
                          <Badge variant="outline" className="text-[10px]">{isApi ? round.type?.replace(/_/g, " ") : "round"}</Badge>
                          <ApprovalBadge status="pending" />
                        </div>
                        {(startDate || endDate) && (
                          <span className="text-xs text-muted-foreground">{startDate || "?"} → {endDate || "?"}</span>
                        )}
                      </div>
                      {criteria.length > 0 && (
                        <div className="space-y-1.5">
                          <p className="text-xs text-muted-foreground font-medium">Scoring</p>
                          <div className="flex flex-wrap gap-2">
                            {criteria.map((c: any) => (
                              <span key={c.criterion_id || c.name} className="text-xs bg-muted/50 rounded-lg px-2 py-1">
                                {c.name} <span className="font-medium">{c.weight}%</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {isApi && round.deliverables?.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {round.deliverables.map((d: any) => (
                            <span key={d.name} className="text-xs border border-border/50 rounded-lg px-2 py-1 text-muted-foreground">
                              {d.name} ({d.type})
                            </span>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          {/* Judges Tab */}
          <TabsContent value="judges">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {(apiJudges.length > 0 ? apiJudges : eventJudges.length > 0 ? eventJudges : mockJudges).map((j: any, i: number) => {
                const isApi = apiJudges.length > 0;
                const name = j.name || "Judge";
                const company = isApi ? j.company : j.institution;
                const expertise: string[] = isApi ? (j.expertise || []) : (j.expertise || []);
                return (
                  <motion.div key={j.judge_id || j.id || i} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                    <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                      <CardContent className="p-4">
                        <div className="flex items-center gap-3 mb-3">
                          <Avatar className="h-10 w-10">
                            <AvatarFallback className="bg-primary/10 text-primary text-xs">
                              {name.split(" ").map((n: string) => n[0]).join("").slice(0, 2)}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-semibold text-sm">{name}</p>
                            <p className="text-xs text-muted-foreground">{company || ""}</p>
                          </div>
                        </div>
                        <div className="flex gap-1 flex-wrap mb-2">
                          {expertise.map((e: string) => <Badge key={e} variant="outline" className="text-[9px]">{e}</Badge>)}
                        </div>
                        {j.email && <p className="text-xs text-muted-foreground">{j.email}</p>}
                        {j.rating && <p className="text-xs text-muted-foreground mt-1">Rating: {j.rating}/5.0</p>}
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          </TabsContent>

          {/* Prizes Tab */}
          <TabsContent value="prizes">
            {prizes ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3 mb-2">
                  <Trophy className="h-5 w-5 text-amber-500" />
                  <span className="text-lg font-bold">{prizes.total_pool}</span>
                  <span className="text-sm text-muted-foreground">total prize pool</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {(prizes.distribution || []).map((d: any, i: number) => (
                    <motion.div key={d.rank || i} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                      <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                        <CardContent className="p-4 text-center space-y-1">
                          <p className="text-2xl font-bold text-amber-500">{d.amount}</p>
                          <p className="font-semibold">{d.title}</p>
                          {d.description && <p className="text-xs text-muted-foreground">{d.description}</p>}
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                  {(prizes.special_awards || []).map((a: any, i: number) => (
                    <motion.div key={a.name || i} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: (prizes.distribution?.length + i) * 0.05 }}>
                      <Card className="border-border/50 bg-card/80 backdrop-blur-sm border-dashed">
                        <CardContent className="p-4 text-center space-y-1">
                          <p className="text-2xl font-bold text-violet-500">{a.amount}</p>
                          <p className="font-semibold">{a.name}</p>
                          {a.description && <p className="text-xs text-muted-foreground">{a.description}</p>}
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>
                {prizes.certificates && (
                  <div className="flex gap-2 flex-wrap pt-2">
                    {prizes.certificates.participant_certificate && <Badge variant="outline">Participant Certificate</Badge>}
                    {prizes.certificates.winner_certificate && <Badge variant="outline">Winner Certificate</Badge>}
                    {prizes.certificates.finalist_certificate && <Badge variant="outline">Finalist Certificate</Badge>}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No prize information available.</p>
            )}
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

          {/* Submissions Tab */}
          <TabsContent value="submissions">
            <div className="space-y-3">
              {eventSubs.length === 0 ? (
                <p className="text-sm text-muted-foreground">No submissions yet.</p>
              ) : eventSubs.map((sub, i) => (
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
                        </div>
                        {sub.feedback && <p className="text-xs mt-2 text-muted-foreground italic">&quot;{sub.feedback}&quot;</p>}
                      </div>
                      <div className="flex items-center gap-4">
                        {sub.score !== null && (
                          <div className="text-center"><p className="text-lg font-bold">{sub.score}</p><p className="text-[10px] text-muted-foreground">Score</p></div>
                        )}
                        <Button variant="outline" size="sm" onClick={() => toast.info("Opening submission details...")}><Eye className="h-3.5 w-3.5" /></Button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </TabsContent>

          {/* Comms Tab */}
          <TabsContent value="comms">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { platform: "Email", icon: Mail, count: "0 sent", status: "Pending", lastSent: "—", desc: "Automated round reminders and updates" },
                { platform: "WhatsApp", icon: MessageSquare, count: "0 groups", status: "Pending", lastSent: "—", desc: "Team coordination and announcements" },
                { platform: "Discord", icon: Globe, count: "0 servers", status: "Pending", lastSent: "—", desc: "Real-time participant support channel" },
              ].map((c) => (
                <Card key={c.platform} className="border-border/50 bg-card/80 backdrop-blur-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="rounded-lg bg-primary/10 p-2"><c.icon className="h-4 w-4 text-primary" /></div>
                      <div><p className="font-semibold text-sm">{c.platform}</p><p className="text-xs text-muted-foreground">{c.desc}</p></div>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">{c.count} • Last: {c.lastSent}</span>
                      <ApprovalBadge status="pending" />
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
