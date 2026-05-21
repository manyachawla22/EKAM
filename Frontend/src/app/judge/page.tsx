"use client";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useState } from "react";
import { mockSubmissions, mockEvents, mockJudges } from "@/lib/mock-data";
import { ApprovalBadge } from "@/components/approval-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { motion } from "framer-motion";
import { toast } from "sonner";
import Link from "next/link";
import {
  Gavel, FileText, AlertTriangle, Send, BarChart3, CheckCircle2,
  Clock, Eye, Zap, ArrowRight, Star, Moon, Sun, Download
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { ThemeToggle } from "@/components/theme-toggle";

const rubricCriteria = [
  { name: "Innovation", weight: 25, desc: "Novelty and creativity of the solution" },
  { name: "Technical Depth", weight: 25, desc: "Code quality, architecture, and engineering" },
  { name: "Impact", weight: 20, desc: "Real-world applicability and potential" },
  { name: "Presentation", weight: 15, desc: "Demo quality, pitch clarity, and slides" },
  { name: "Completeness", weight: 15, desc: "Feature completion and polish" },
];

export default function JudgeDashboard() {
  const { theme, toggleTheme } = useAppStore();
  const [selectedSub, setSelectedSub] = useState(mockSubmissions[0]);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [feedback, setFeedback] = useState("");

  const getScore = (criterion: string) => scores[criterion] ?? 70;
  const totalScore = rubricCriteria.reduce((sum, c) => sum + (getScore(c.name) * c.weight / 100), 0);

  return (
    <ProtectedRoute allowedRoles={["judge", "admin"]}>
    <div className="min-h-screen">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto flex items-center justify-between h-14 px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                <Zap className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold">Ekam</span>
            </Link>
            <Badge variant="outline" className="text-[10px] ml-2">Judge Panel</Badge>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Avatar className="h-8 w-8"><AvatarFallback className="bg-primary/10 text-primary text-xs">RI</AvatarFallback></Avatar>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Judge Dashboard</h1>
          <p className="text-sm text-muted-foreground">Welcome, Dr. Rajesh Iyer. You have {mockSubmissions.filter((s) => s.status === "pending").length} pending reviews.</p>
        </div>

        {/* Assigned Events */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {mockEvents.filter((e) => e.status === "active").map((ev) => (
            <Card key={ev.id} className="border-border/50 bg-card/80 backdrop-blur-sm hover:border-primary/20 transition-all">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="font-semibold text-sm">{ev.name}</p>
                  <ApprovalBadge status="in_progress" />
                </div>
                <p className="text-xs text-muted-foreground mb-3">{ev.type} • Stage: {ev.stage}</p>
                <Button variant="outline" size="sm" className="w-full text-xs" render={<Link href={`/event/${ev.hash}`} />}>
                  View Event <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        <Tabs defaultValue="review" className="space-y-4">
          <TabsList>
            <TabsTrigger value="review">Submission Review</TabsTrigger>
            <TabsTrigger value="anomalies">Anomaly Detection</TabsTrigger>
          </TabsList>

          {/* Review Tab */}
          <TabsContent value="review">
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Submissions list */}
              <div className="lg:col-span-2 space-y-3">
                <h3 className="text-sm font-semibold text-muted-foreground mb-2">Submissions ({mockSubmissions.length})</h3>
                {mockSubmissions.map((sub, i) => (
                  <motion.div key={sub.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}>
                    <Card
                      className={`border-border/50 cursor-pointer transition-all ${selectedSub?.id === sub.id ? "border-primary bg-primary/5" : "bg-card/80 hover:border-primary/20"}`}
                      onClick={() => { setSelectedSub(sub); setFeedback(sub.feedback); }}
                    >
                      <CardContent className="p-3">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-sm">{sub.teamName}</p>
                          <ApprovalBadge status={sub.status === "reviewed" ? "completed" : sub.status === "flagged" ? "flagged" : sub.status === "finalised" ? "approved" : "pending"} />
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                          <span>{sub.round}</span>
                          <span>{sub.attachments.length} files</span>
                          {sub.score && <span className="font-medium text-foreground">Score: {sub.score}</span>}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>

              {/* Grading Panel */}
              <div className="lg:col-span-3 space-y-4">
                {selectedSub && (
                  <>
                    <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base">{selectedSub.teamName} — Grading</CardTitle>
                          <div className="text-right">
                            <p className="text-2xl font-bold gradient-text">{Math.round(totalScore)}</p>
                            <p className="text-[10px] text-muted-foreground">Weighted Score</p>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-5">
                        <div>
                          <p className="text-xs text-muted-foreground mb-2">Team Members</p>
                          <div className="flex gap-2 flex-wrap">
                            {selectedSub.members.map((m) => <Badge key={m} variant="outline" className="text-xs">{m}</Badge>)}
                          </div>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground mb-2">Attachments</p>
                          <div className="flex gap-2 flex-wrap">
                            {selectedSub.attachments.map((a) => (
                              <div key={a} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/30 bg-muted/20 text-xs">
                                <FileText className="h-3 w-3" />{a}
                              </div>
                            ))}
                          </div>
                        </div>
                        {/* Rubric */}
                        <div className="space-y-4">
                          <p className="text-xs font-semibold text-muted-foreground">Evaluation Rubric</p>
                          {rubricCriteria.map((c) => (
                            <div key={c.name} className="space-y-2">
                              <div className="flex items-center justify-between text-sm">
                                <span className="font-medium">{c.name} <span className="text-muted-foreground text-xs">({c.weight}%)</span></span>
                                <span className="font-bold text-primary">{getScore(c.name)}</span>
                              </div>
                              <p className="text-[10px] text-muted-foreground">{c.desc}</p>
                              <Slider
                                value={[getScore(c.name)]}
                                onValueChange={(v) => setScores({ ...scores, [c.name]: Array.isArray(v) ? v[0] : v })}
                                max={100}
                                step={1}
                                className="w-full"
                              />
                            </div>
                          ))}
                        </div>
                        {/* Feedback */}
                        <div>
                          <p className="text-xs font-semibold text-muted-foreground mb-2">Written Feedback</p>
                          <Textarea
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                            placeholder="Share your detailed evaluation feedback..."
                            rows={4}
                          />
                        </div>
                        <div className="flex gap-3">
                          <Button variant="outline" className="flex-1" onClick={() => toast.info("Feedback sent to team")}>
                            <Send className="h-3.5 w-3.5 mr-1.5" />Send Feedback
                          </Button>
                          <Button className="flex-1 bg-primary hover:bg-primary/90" onClick={() => toast.success("Evaluation submitted!")}>
                            <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />Submit Evaluation
                          </Button>
                        </div>
                        <Button variant="outline" className="w-full" onClick={() => toast.success("Report generated!")}>
                          <BarChart3 className="h-3.5 w-3.5 mr-1.5" />Generate Report
                        </Button>
                      </CardContent>
                    </Card>
                  </>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Anomalies Tab */}
          <TabsContent value="anomalies" className="space-y-4">
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm border-red-500/20">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-400" />Score Divergence Alerts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockSubmissions.filter((s) => s.status === "flagged").map((sub) => (
                  <div key={sub.id} className="p-4 rounded-xl border border-red-500/20 bg-red-500/5">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-red-400" />
                        <p className="font-semibold text-sm">{sub.teamName}</p>
                        <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20 text-[10px]">Flagged</Badge>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-3">
                      <div className="text-center p-3 rounded-lg bg-background/50">
                        <p className="text-2xl font-bold">{sub.score}</p>
                        <p className="text-xs text-muted-foreground">Your Score</p>
                      </div>
                      <div className="text-center p-3 rounded-lg bg-background/50">
                        <p className="text-2xl font-bold text-muted-foreground">{sub.panelAvg}</p>
                        <p className="text-xs text-muted-foreground">Panel Average</p>
                      </div>
                    </div>
                    <p className="text-xs text-red-400 mt-3">{sub.feedback}</p>
                    <div className="flex gap-2 mt-3">
                      <Button variant="outline" size="sm" className="text-xs flex-1">Review Score</Button>
                      <Button variant="outline" size="sm" className="text-xs flex-1">Justify</Button>
                    </div>
                  </div>
                ))}
                {mockSubmissions.filter((s) => s.status !== "flagged").length > 0 && (
                  <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      <p className="text-sm font-medium">Other submissions are within acceptable score ranges.</p>
                    </div>
                  </div>
                )}
                </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      <EvaluationModal 
        isOpen={isEvalModalOpen} 
        onClose={() => setIsEvalModalOpen(false)} 
        submission={evaluatingSubmission} 
      />
    </div>
    </ProtectedRoute>
  );
}
