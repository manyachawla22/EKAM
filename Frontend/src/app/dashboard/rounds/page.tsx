"use client";
import { mockEvents } from "@/lib/mock-data";
import { ApprovalBadge } from "@/components/approval-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { motion } from "framer-motion";
import { Layers } from "lucide-react";

export default function RoundsPage() {
  const allRounds = mockEvents.flatMap((e) => e.rounds.map((r) => ({ ...r, eventName: e.name })));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Rounds</h1>
        <p className="text-sm text-muted-foreground">{allRounds.length} rounds across all events</p>
      </div>

      <div className="space-y-4">
        {mockEvents.filter((e) => e.rounds.length > 0).map((event) => (
          <Card key={event.id} className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" />{event.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {event.rounds.map((round, i) => (
                <motion.div key={round.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-3 rounded-xl bg-muted/10 border border-border/20">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-sm">{round.name}</p>
                        <ApprovalBadge status={round.status === "completed" ? "completed" : round.status === "active" ? "in_progress" : "pending"} />
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{round.startDate} → {round.endDate}</p>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <div className="text-right">
                        <p className="font-medium">{round.participantsAdvanced}/{round.totalParticipants}</p>
                        <p className="text-[10px] text-muted-foreground">Advanced</p>
                      </div>
                      {round.totalParticipants > 0 && (
                        <Progress value={(round.participantsAdvanced / round.totalParticipants) * 100} className="w-24 h-1.5" />
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
