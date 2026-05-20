"use client";
import { scoreDistribution, roundComparison, teamBalanceData, mockSubmissions, mockParticipants } from "@/lib/mock-data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApprovalBadge } from "@/components/approval-badge";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, Legend, AreaChart, Area } from "recharts";
import { Download, Share2, FileText, AlertTriangle, Trophy, BarChart3, TrendingUp, Printer } from "lucide-react";

const COLORS = ["#CC0000", "#d97706", "#92400e", "#4d7c0f", "#7f1d1d", "#a16207"];
const HEX_COLORS = ["#CC0000", "#d97706", "#92400e", "#4d7c0f", "#7f1d1d", "#a16207"];

const leaderboard = [
  { rank: 1, team: "Neural Ninjas", score: 92, change: "↑ 2", badge: "🥇" },
  { rank: 2, team: "PixelPioneers", score: 90, change: "—", badge: "🥈" },
  { rank: 3, team: "CodeCrafters", score: 87, change: "↓ 1", badge: "🥉" },
  { rank: 4, team: "ByteForce", score: 84, change: "↑ 1", badge: "" },
  { rank: 5, team: "DataDragons", score: 80, change: "↓ 1", badge: "" },
  { rank: 6, team: "QuantumLeap", score: 78, change: "↑ 3", badge: "" },
  { rank: 7, team: "AlgoAces", score: 75, change: "—", badge: "" },
  { rank: 8, team: "TechTitans", score: 72, change: "↓ 2", badge: "" },
];

const roundScores = [
  { round: "R1", avg: 65, highest: 95, lowest: 30 },
  { round: "R2", avg: 72, highest: 98, lowest: 42 },
  { round: "R3", avg: 78, highest: 96, lowest: 55 },
];

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Reports & Analytics</h1>
          <p className="text-sm text-muted-foreground">Comprehensive event performance insights and analytics.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => toast.success("Report exported as PDF")}><Download className="h-3.5 w-3.5 mr-1.5" />Export PDF</Button>
          <Button variant="outline" size="sm" onClick={() => toast.info("Share link copied")}><Share2 className="h-3.5 w-3.5 mr-1.5" />Share</Button>
          <Button variant="outline" size="sm" onClick={() => toast.info("Opening print dialog...")}><Printer className="h-3.5 w-3.5 mr-1.5" />Print</Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
          <TabsTrigger value="anomalies">Anomalies</TabsTrigger>
          <TabsTrigger value="comms">Comms Log</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Score Distribution */}
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><BarChart3 className="h-4 w-4 text-primary" />Score Distribution</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={scoreDistribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.26 0.010 40)" />
                    <XAxis dataKey="range" tick={{ fontSize: 11 }} stroke="oklch(0.50 0.01 45)" />
                    <YAxis tick={{ fontSize: 11 }} stroke="oklch(0.50 0.01 45)" />
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.010 40)", border: "1px solid oklch(0.26 0.010 40)", borderRadius: "8px", fontSize: "12px" }} />
                    <Bar dataKey="count" fill="#CC0000" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Team Skill Balance */}
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><TrendingUp className="h-4 w-4 text-primary" />Team Skill Balance</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    <Pie data={teamBalanceData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={4} dataKey="count" nameKey="skill" label={((entry: any) => `${entry.skill} ${(entry.percent * 100).toFixed(0)}%`) as any}>
                      {teamBalanceData.map((_, i) => <Cell key={i} fill={HEX_COLORS[i % HEX_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.010 40)", border: "1px solid oklch(0.26 0.010 40)", borderRadius: "8px", fontSize: "12px" }} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Round Comparison */}
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
              <CardHeader><CardTitle className="text-base">Round-wise Progression</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={roundComparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.26 0.010 40)" />
                    <XAxis dataKey="round" tick={{ fontSize: 11 }} stroke="oklch(0.5 0.02 260)" />
                    <YAxis tick={{ fontSize: 11 }} stroke="oklch(0.50 0.01 45)" />
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.010 40)", border: "1px solid oklch(0.26 0.010 40)", borderRadius: "8px", fontSize: "12px" }} />
                    <Legend />
                    <Bar dataKey="advanced" fill="#10b981" name="Advanced" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="eliminated" fill="#ef4444" name="Eliminated" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Round Score Trends */}
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
              <CardHeader><CardTitle className="text-base">Score Trends by Round</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={roundScores}>
                    <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.26 0.010 40)" />
                    <XAxis dataKey="round" tick={{ fontSize: 11 }} stroke="oklch(0.5 0.02 260)" />
                    <YAxis tick={{ fontSize: 11 }} stroke="oklch(0.5 0.01 55)" />
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.006 55)", border: "1px solid oklch(0.26 0.008 55)", borderRadius: "8px", fontSize: "12px" }} />
                    <Area type="monotone" dataKey="highest" stroke="#10b981" fill="#10b981" fillOpacity={0.1} name="Highest" />
                    <Area type="monotone" dataKey="avg" stroke="#CC0000" fill="#CC0000" fillOpacity={0.15} name="Average" />
                    <Area type="monotone" dataKey="lowest" stroke="#ef4444" fill="#ef4444" fillOpacity={0.1} name="Lowest" />
                    <Legend />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Report Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { title: "Screening Report", desc: "400 screened, 342 advanced", date: "May 01", status: "completed" },
              { title: "OA Performance Report", desc: "Avg score 72/100, top 10% cutoff 90+", date: "May 05", status: "completed" },
              { title: "Hackathon Progress Report", desc: "In progress — 45% submissions expected", date: "May 18", status: "in_progress" },
            ].map((r) => (
              <Card key={r.title} className="border-border/50 bg-card/80 backdrop-blur-sm hover:border-primary/20 transition-all cursor-pointer">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="h-4 w-4 text-primary" />
                    <p className="font-semibold text-sm">{r.title}</p>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">{r.desc}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{r.date}</span>
                    <ApprovalBadge status={r.status as "completed" | "in_progress"} />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Leaderboard */}
        <TabsContent value="leaderboard">
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2"><Trophy className="h-4 w-4 text-amber-500" />Leaderboard — HackSphere 2026</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {leaderboard.map((entry, i) => (
                  <motion.div
                    key={entry.team}
                    initial={{ opacity: 0, x: -15 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className={`flex items-center gap-4 p-3 rounded-xl ${i < 3 ? "bg-primary/5 border border-primary/10" : "bg-muted/10"}`}
                  >
                    <span className="text-lg font-bold w-8 text-center">{entry.badge || entry.rank}</span>
                    <div className="flex-1">
                      <p className="font-semibold text-sm">{entry.team}</p>
                    </div>
                    <Badge variant="outline" className={`text-[10px] ${entry.change.includes("↑") ? "text-emerald-500" : entry.change.includes("↓") ? "text-red-400" : "text-muted-foreground"}`}>
                      {entry.change}
                    </Badge>
                    <div className="text-right">
                      <p className="text-lg font-bold">{entry.score}</p>
                      <p className="text-[10px] text-muted-foreground">pts</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Anomalies */}
        <TabsContent value="anomalies" className="space-y-4">
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm border-red-500/20">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-red-400" />Anomaly Alerts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                  <p className="font-semibold text-sm">Score Divergence — CodeCrafters</p>
                  <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20 text-[10px]">High</Badge>
                </div>
                <p className="text-xs text-muted-foreground">Judge score 91 vs panel average 74 — 17 point divergence exceeds threshold of 10.</p>
                <div className="flex gap-2 mt-3">
                  <Button variant="outline" size="sm" className="text-xs">Investigate</Button>
                  <Button variant="outline" size="sm" className="text-xs">Dismiss</Button>
                </div>
              </div>
              <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <p className="font-semibold text-sm">Submission Timing — QuantumLeap</p>
                  <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px]">Medium</Badge>
                </div>
                <p className="text-xs text-muted-foreground">Submission timestamp is 3 minutes after the official deadline. Review for grace period eligibility.</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Comms Log */}
        <TabsContent value="comms">
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader><CardTitle className="text-base">Communication Log</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {[
                { type: "Email", subject: "Round 3 Reminder", recipients: 342, sent: "May 18, 2:00 PM", status: "delivered" },
                { type: "Email", subject: "Submission Guidelines", recipients: 342, sent: "May 17, 10:00 AM", status: "delivered" },
                { type: "WhatsApp", subject: "Mentor Session Reminder", recipients: 68, sent: "May 18, 1:00 PM", status: "delivered" },
                { type: "Discord", subject: "API Sandbox Announcement", recipients: 500, sent: "May 17, 6:00 PM", status: "delivered" },
                { type: "Email", subject: "Welcome to HackSphere 2026", recipients: 500, sent: "May 15, 9:00 AM", status: "delivered" },
              ].map((log, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-border/20 last:border-0">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="text-[10px] min-w-[60px] justify-center">{log.type}</Badge>
                    <div>
                      <p className="text-sm font-medium">{log.subject}</p>
                      <p className="text-xs text-muted-foreground">{log.recipients} recipients • {log.sent}</p>
                    </div>
                  </div>
                  <ApprovalBadge status="completed" />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
