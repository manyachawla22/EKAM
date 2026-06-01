"use client";
import { use, useState, useEffect } from "react";
import Link from "next/link";
import { useAppStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  ArrowLeft, Download, Share2, Loader, TrendingUp, BarChart3,
  FileText, Target, Zap
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

interface PerformanceReport {
  participant_name: string;
  team_name: string;
  report_html: string;
  statistics: {
    overall_average: number;
    best_score: number;
    worst_score: number;
    rounds_participated: number;
    total_evaluations: number;
    flagged_submissions: number;
    progression: string;
  };
  round_details: Array<{
    round_number: number;
    round_name: string;
    score: number;
    judge_count: number;
    status: string;
    feedback?: string;
  }>;
}

export default function PerformanceReportPage({
  params,
}: {
  params: Promise<{ participantId: string }>;
}) {
  const { participantId } = use(params);
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        setLoading(true);
        // Get event from mock data or query params
        const response = await fetch(
          `/api/reports/participant/[event_id]/${participantId}`
        );
        if (!response.ok) {
          throw new Error("Failed to fetch performance report");
        }
        const data = await response.json();
        setReport(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load report"
        );
        toast.error("Failed to load performance report");
      } finally {
        setLoading(false);
      }
    };

    if (participantId) {
      fetchReport();
    }
  }, [participantId]);

  const handleDownloadPDF = () => {
    toast.success("Downloading performance report as PDF...");
    // Implement PDF download if needed
  };

  const handleShare = () => {
    toast.info("Share link copied to clipboard");
    // Implement share functionality
  };

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto flex items-center justify-between h-14 px-4 sm:px-6">
          <Link
            href={`/portal/${participantId}`}
            className="flex items-center gap-2 hover:text-primary transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="text-sm font-medium">Back to Portal</span>
          </Link>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px]">
              Performance Report
            </Badge>
            <ThemeToggle />
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : error ? (
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardContent className="p-6">
              <div className="text-center">
                <p className="text-muted-foreground mb-4">{error}</p>
                <Button asChild variant="outline">
                  <Link href={`/portal/${participantId}`}>
                    Return to Portal
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : report ? (
          <>
            {/* Header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">
                    Performance Report
                  </h1>
                  <p className="text-sm text-muted-foreground mt-1">
                    {report.participant_name} • Team {report.team_name}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDownloadPDF}
                  >
                    <Download className="h-3.5 w-3.5 mr-1.5" />
                    Export
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleShare}
                  >
                    <Share2 className="h-3.5 w-3.5 mr-1.5" />
                    Share
                  </Button>
                </div>
              </div>
            </motion.div>

            {/* Key Statistics */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
            >
              {[
                {
                  label: "Overall Average",
                  value: `${report.statistics.overall_average.toFixed(1)}/100`,
                  icon: TrendingUp,
                  color: "text-blue-500",
                },
                {
                  label: "Best Score",
                  value: `${report.statistics.best_score.toFixed(1)}`,
                  icon: Target,
                  color: "text-green-500",
                },
                {
                  label: "Rounds",
                  value: report.statistics.rounds_participated,
                  icon: BarChart3,
                  color: "text-purple-500",
                },
                {
                  label: "Progression",
                  value: report.statistics.progression.charAt(0).toUpperCase() +
                    report.statistics.progression.slice(1),
                  icon: Zap,
                  color: "text-orange-500",
                },
              ].map((stat, i) => (
                <Card
                  key={stat.label}
                  className="border-border/50 bg-card/80 backdrop-blur-sm hover:border-primary/20 transition-all"
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">
                          {stat.label}
                        </p>
                        <p className="text-2xl font-bold">{stat.value}</p>
                      </div>
                      <stat.icon className={`h-8 w-8 ${stat.color} opacity-60`} />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </motion.div>

            {/* Round-by-Round Performance */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    Round-by-Round Performance
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {report.round_details.map((round, i) => (
                    <div
                      key={round.round_number}
                      className="space-y-2 pb-4 border-b border-border/50 last:border-0 last:pb-0"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-semibold">
                            {round.round_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {round.judge_count} judge{round.judge_count !== 1 ? "s" : ""} evaluated
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-primary">
                            {round.score.toFixed(1)}/100
                          </p>
                          <Badge variant="outline" className="text-[10px]">
                            {round.status}
                          </Badge>
                        </div>
                      </div>
                      <Progress
                        value={round.score}
                        className="h-2"
                      />
                      {round.feedback && (
                        <p className="text-xs text-muted-foreground italic mt-2">
                          💭 {round.feedback}
                        </p>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </motion.div>

            {/* LLM Generated Report */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    Performance Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div
                    className="prose prose-sm dark:prose-invert max-w-none"
                    dangerouslySetInnerHTML={{ __html: report.report_html }}
                  />
                </CardContent>
              </Card>
            </motion.div>
          </>
        ) : null}
      </div>
    </div>
  );
}
