"use client";
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Send, Bot, User, Sparkles, Eye, Save, Rocket, Loader2, Check } from "lucide-react";

interface Message { role: "assistant" | "user"; content: string; }

const wizardSteps = [
  { question: "What would you like to name your event?", field: "name", placeholder: "e.g., HackSphere 2026" },
  { question: "What type of event is this?", field: "type", placeholder: "Hackathon, Case Competition, Coding Contest..." },
  { question: "How many participants per team?", field: "teamSize", placeholder: "e.g., 3-5" },
  { question: "What stages will your event have? (comma separated)", field: "stages", placeholder: "e.g., Registration, Screening, OA, Hackathon, Judging" },
  { question: "What are the key rules?", field: "rules", placeholder: "e.g., No plagiarism, 48-hour time limit..." },
  { question: "How should participants be evaluated? (evaluation model)", field: "evaluation", placeholder: "e.g., Rubric-based judging, peer review..." },
  { question: "Any submission requirements?", field: "submissions", placeholder: "e.g., GitHub repo, demo video, pitch deck..." },
  { question: "Communication preferences? (email, WhatsApp, Discord)", field: "comms", placeholder: "e.g., Email + Discord" },
];

export default function CreateEventPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "👋 Hi! I'm the Ekam configuration assistant. I'll help you set up your event step by step. Let's start — what would you like to name your event?" },
  ]);
  const [input, setInput] = useState("");
  const [step, setStep] = useState(0);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);

    const currentStep = wizardSteps[step];
    if (currentStep) {
      setConfig((prev) => ({ ...prev, [currentStep.field]: userMsg }));
    }

    setTyping(true);
    await new Promise((r) => setTimeout(r, 800 + Math.random() * 700));
    setTyping(false);

    const nextStep = step + 1;
    if (nextStep < wizardSteps.length) {
      const ack = getAck(step, userMsg);
      setMessages((prev) => [...prev, { role: "assistant", content: `${ack}\n\n${wizardSteps[nextStep].question}` }]);
      setStep(nextStep);
    } else {
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: "🎉 Excellent! I've captured all the details. Your event configuration is ready! You can preview the schema, save as draft, or deploy the event using the buttons on the right panel.",
      }]);
      setStep(nextStep);
    }
  };

  const getAck = (s: number, val: string): string => {
    const acks = [
      `Great name! "${val}" sounds like an exciting event.`,
      `Perfect — a ${val} it is!`,
      `Got it, ${val} members per team.`,
      `Nice pipeline! I've mapped out the stages.`,
      `Rules noted and configured.`,
      `Evaluation model set to: ${val}.`,
      `Submission requirements captured.`,
      `Communication channels configured.`,
    ];
    return acks[s] || "Got it!";
  };

  const isComplete = step >= wizardSteps.length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Create New Event</h1>
        <p className="text-sm text-muted-foreground">Use our intelligent wizard to configure your event step by step.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Chat */}
        <Card className="lg:col-span-3 border-border/50 bg-card/80 backdrop-blur-sm flex flex-col h-[600px]">
          <CardHeader className="pb-3 border-b border-border/30">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-primary/10 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <div>
                <CardTitle className="text-sm">Ekam Configuration Assistant</CardTitle>
                <p className="text-[10px] text-muted-foreground">Step {Math.min(step + 1, wizardSteps.length)} of {wizardSteps.length}</p>
              </div>
            </div>
          </CardHeader>
          <ScrollArea className="flex-1 p-4" ref={scrollRef}>
            <div className="space-y-4">
              <AnimatePresence>
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
                  >
                    {msg.role === "assistant" && (
                      <div className="rounded-full bg-primary/10 h-7 w-7 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="h-3.5 w-3.5 text-primary" />
                      </div>
                    )}
                    <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-line ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground rounded-br-md"
                        : "bg-muted/50 rounded-bl-md"
                    }`}>
                      {msg.content}
                    </div>
                    {msg.role === "user" && (
                      <div className="rounded-full bg-muted h-7 w-7 flex items-center justify-center shrink-0 mt-0.5">
                        <User className="h-3.5 w-3.5" />
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
              {typing && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
                  <div className="rounded-full bg-primary/10 h-7 w-7 flex items-center justify-center shrink-0">
                    <Bot className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div className="bg-muted/50 rounded-2xl rounded-bl-md px-4 py-3 flex gap-1">
                    <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </motion.div>
              )}
            </div>
          </ScrollArea>
          <div className="p-4 border-t border-border/30">
            <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={wizardSteps[step]?.placeholder || "Type your response..."}
                disabled={isComplete}
                className="flex-1"
              />
              <Button type="submit" size="icon" disabled={isComplete || typing}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </Card>

        {/* Side panel */}
        <div className="lg:col-span-2 space-y-4">
          {/* Summary */}
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Event Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {wizardSteps.map((ws) => (
                <div key={ws.field} className="flex items-start justify-between gap-2">
                  <span className="text-xs text-muted-foreground capitalize">{ws.field.replace(/([A-Z])/g, " $1")}</span>
                  {config[ws.field] ? (
                    <Badge variant="outline" className="text-[10px] max-w-[180px] truncate">{config[ws.field]}</Badge>
                  ) : (
                    <span className="text-[10px] text-muted-foreground/50 italic">Not set</span>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* JSON Preview */}
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Schema Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-[10px] font-mono bg-muted/30 rounded-xl p-3 overflow-auto max-h-48 text-muted-foreground">
                {JSON.stringify({
                  eventId: "EF-" + Math.random().toString(36).substr(2, 6).toUpperCase(),
                  ...config,
                  createdAt: new Date().toISOString(),
                  status: "draft",
                }, null, 2)}
              </pre>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="space-y-2">
            <Dialog>
              <DialogTrigger render={
                <Button variant="outline" className="w-full" disabled={Object.keys(config).length === 0} />
              }>
                <Eye className="h-4 w-4 mr-2" />Preview Configuration
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>Event Configuration Preview</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  {Object.entries(config).map(([key, val]) => (
                    <div key={key} className="flex items-start justify-between border-b border-border/30 pb-2">
                      <span className="text-sm font-medium capitalize">{key.replace(/([A-Z])/g, " $1")}</span>
                      <span className="text-sm text-muted-foreground text-right max-w-[60%]">{val}</span>
                    </div>
                  ))}
                  {Object.keys(config).length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">No configuration data yet. Answer the assistant&apos;s questions to build your event schema.</p>
                  )}
                </div>
              </DialogContent>
            </Dialog>
            <Button
              variant="outline" className="w-full"
              onClick={() => { toast.success("Draft saved successfully!"); }}
              disabled={Object.keys(config).length === 0}
            >
              <Save className="h-4 w-4 mr-2" />Save Draft
            </Button>
            <Button
              className="w-full bg-primary hover:bg-primary/90"
              onClick={() => { toast.success("Event deployed! Redirecting..."); }}
              disabled={!isComplete}
            >
              <Rocket className="h-4 w-4 mr-2" />Deploy Event
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
