"use client";
import { mockJudges } from "@/lib/mock-data";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Star, Mail, Plus } from "lucide-react";
import { toast } from "sonner";

export default function JudgesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Judges</h1>
          <p className="text-sm text-muted-foreground">{mockJudges.length} judges in your pool</p>
        </div>
        <Button variant="outline" onClick={() => toast.info("Invite judge flow...")}><Plus className="h-4 w-4 mr-2" />Invite Judge</Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {mockJudges.map((j, i) => (
          <motion.div key={j.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm hover:border-primary/20 transition-all">
              <CardContent className="p-5">
                <div className="flex items-center gap-3 mb-4">
                  <Avatar className="h-12 w-12">
                    <AvatarFallback className="bg-primary/10 text-primary font-semibold">{j.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold">{j.name}</p>
                    <p className="text-xs text-muted-foreground">{j.institution}</p>
                  </div>
                  <div className="flex items-center gap-0.5 text-amber-500">
                    <Star className="h-3.5 w-3.5 fill-amber-500" />
                    <span className="text-xs font-semibold">{j.rating}</span>
                  </div>
                </div>
                <div className="flex gap-1.5 flex-wrap mb-3">
                  {j.expertise.map((e) => <Badge key={e} variant="outline" className="text-[10px]">{e}</Badge>)}
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{j.email}</span>
                  <span>{j.assignedEvents.length} events</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
