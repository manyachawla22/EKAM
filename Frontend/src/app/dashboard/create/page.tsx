"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Send, Bot, User, Sparkles, Save, Rocket, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { aiApi } from "@/lib/api";

interface Message {
  role: "assistant" | "user";
  content: string;
}

interface EventConfig {
  event_id?: string;
  core?: {
    name?: string;
    event_type?: string;
    theme?: string;
    mode?: string;
    description?: string;
    venue?: { name?: string; city?: string; country?: string };
    contact?: { email?: string; phone?: string };
  };
  timeline?: {
    registration?: { opens_at?: string; closes_at?: string };
    key_dates?: { name: string; date: string }[];
  };
  participants?: {
    team?: { min_size?: number; max_size?: number };
    capacity?: { max_teams?: number; max_participants?: number };
    eligibility?: { open_to?: string[] };
  };
  rounds?: { round_name?: string; type?: string }[];
  judging_panel?: { judges?: { name: string }[] };
  prizes?: { total_pool?: string; distribution?: { rank: number; title: string; amount: string }[] };
  [key: string]: unknown;
}

const INITIAL_MESSAGE =
  "Hi! I'm Ekam's event builder AI.\n\nDescribe your event in as much detail as you'd like — the more you share upfront, the less I'll need to ask. For example:\n\n\"Run a case competition. 50 teams of 4. Theme: Sustainable Supply Chain. Two rounds: Prelims (slide deck + executive summary), Finals (live presentation). Scoring: Problem Analysis 25%, Solution 35%, Feasibility 20%, Presentation 20%. Top 10 to finals. 3 industry judges. Registration opens next Monday for 10 days, prelims submission 7 days later, finals on last Saturday. Prize pool ₹50,000.\"\n\nOr just start with the basics and we'll build from there!";

function SummaryRow({ label, value }: { label: string; value?: string | number }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex items-start justify-between gap-3 py-1.5 border-b border-border/20 last:border-0">
      <span className="text-[11px] text-muted-foreground shrink-0">{label}</span>
      <span className="text-[11px] font-medium text-right truncate max-w-[160px]">{value}</span>
    </div>
  );
}

export default function CreateEventPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: INITIAL_MESSAGE },
  ]);
  const [input, setInput] = useState("");
  const [config, setConfig] = useState<EventConfig>({});
  const [eventId, setEventId] = useState<string | null>(null);
  const [typing, setTyping] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, typing]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || typing) return;
    setInput("");
    setError(null);

    const updatedMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(updatedMessages);
    setTyping(true);

    try {
      const apiMessages = updatedMessages.map((m) => ({ role: m.role, content: m.content }));
      const result = await aiApi.chat(apiMessages, eventId);

      const aiMessage: string = result.message ?? "Got it!";
      const newConfig: EventConfig = result.event_config ?? config;
      const complete: boolean = result.is_complete ?? false;

      if (result.event_id) setEventId(result.event_id);
      setConfig(newConfig);
      setIsComplete(complete);
      setMessages((prev) => [...prev, { role: "assistant", content: aiMessage }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong. Is the backend running?";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ " + msg },
      ]);
    } finally {
      setTyping(false);
    }
  };

  const handleSaveDraft = async () => {
    if (Object.keys(config).length === 0) return;
    setSaving(true);
    try {
      const result = await aiApi.saveConfig(config, eventId);
      toast.success(`Draft saved! (${result.filename})`);
    } catch {
      toast.error("Failed to save draft.");
    } finally {
      setSaving(false);
    }
  };

  const handleDeploy = async () => {
    if (!isComplete) return;
    setSaving(true);
    try {
      const result = await aiApi.deploy(config, eventId);
      toast.success(`Event deployed! Hash: ${result.hash}`);
      router.push("/dashboard/events");
    } catch {
      toast.error("Failed to deploy event.");
      setSaving(false);
    }
  };

  const hasConfig = Object.keys(config).length > 0;
  const configJson = JSON.stringify(config, null, 2);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Create New Event</h1>
        <p className="text-sm text-muted-foreground">Describe your event — our AI will build the full configuration.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Chat panel */}
        <Card className="lg:col-span-3 border-border/50 bg-card/80 backdrop-blur-sm flex flex-col h-[640px]">
          <CardHeader className="pb-3 border-b border-border/30 shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-sm">Ekam Event Builder</CardTitle>
                  <p className="text-[10px] text-muted-foreground">Powered by Gemini</p>
                </div>
              </div>
              {isComplete && (
                <div className="flex items-center gap-1.5 text-emerald-500">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="text-xs font-medium">Config complete</span>
                </div>
              )}
              {error && !isComplete && (
                <div className="flex items-center gap-1.5 text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-xs">Backend unreachable</span>
                </div>
              )}
            </div>
          </CardHeader>

          <div className="flex-1 p-4 overflow-y-auto min-h-0" ref={scrollRef}>
            <div className="space-y-4">
              <AnimatePresence initial={false}>
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
                  >
                    {msg.role === "assistant" && (
                      <div className="rounded-full bg-primary/10 h-7 w-7 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="h-3.5 w-3.5 text-primary" />
                      </div>
                    )}
                    <div
                      className={`max-w-[82%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-line leading-relaxed ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground rounded-br-md"
                          : "bg-muted/50 rounded-bl-md"
                      }`}
                    >
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
                  <div className="bg-muted/50 rounded-2xl rounded-bl-md px-4 py-3 flex gap-1 items-center">
                    <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </motion.div>
              )}
            </div>
          </div>

          <div className="p-4 border-t border-border/30 shrink-0">
            <form
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="flex gap-2"
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  isComplete
                    ? "Config ready — keep chatting to refine or correct anything"
                    : "Describe your event or answer the question..."
                }
                disabled={typing}
                className="flex-1"
              />
              <Button type="submit" size="icon" disabled={typing || !input.trim()}>
                {typing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
          </div>
        </Card>

        {/* Right panel */}
        <div className="lg:col-span-2 space-y-4">
          {/* Live summary */}
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Event Summary</CardTitle>
            </CardHeader>
            <CardContent>
              {!hasConfig ? (
                <p className="text-[11px] text-muted-foreground italic text-center py-3">
                  Start chatting to see your event config appear here.
                </p>
              ) : (
                <div className="space-y-0.5">
                  <SummaryRow label="Name" value={config.core?.name} />
                  <SummaryRow label="Type" value={config.core?.event_type} />
                  <SummaryRow label="Theme" value={config.core?.theme} />
                  <SummaryRow label="Mode" value={config.core?.mode} />
                  <SummaryRow
                    label="Team size"
                    value={
                      config.participants?.team?.min_size != null
                        ? `${config.participants.team.min_size}–${config.participants.team.max_size}`
                        : undefined
                    }
                  />
                  <SummaryRow label="Max teams" value={config.participants?.capacity?.max_teams} />
                  <SummaryRow
                    label="Eligibility"
                    value={[config.participants?.eligibility?.open_to].flat().filter(Boolean).join(", ")}
                  />
                  <SummaryRow label="Rounds" value={config.rounds?.length} />
                  <SummaryRow label="Judges" value={config.judging_panel?.judges?.length} />
                  <SummaryRow label="Prize pool" value={config.prizes?.total_pool} />
                  <SummaryRow label="Contact" value={config.core?.contact?.email} />
                  <SummaryRow
                    label="Venue"
                    value={config.core?.venue?.city}
                  />
                  <SummaryRow label="Reg opens" value={config.timeline?.registration?.opens_at?.slice(0, 10)} />
                  <SummaryRow label="Reg closes" value={config.timeline?.registration?.closes_at?.slice(0, 10)} />
                </div>
              )}
            </CardContent>
          </Card>

          {/* JSON preview */}
          <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Schema Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-[10px] font-mono bg-muted/30 rounded-xl p-3 overflow-auto max-h-52 text-muted-foreground leading-relaxed">
                {hasConfig ? configJson : '{\n  // Config will appear here\n}'}
              </pre>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="space-y-2">
            <Button
              variant="outline"
              className="w-full"
              onClick={handleSaveDraft}
              disabled={!hasConfig || saving}
            >
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              Save Draft
            </Button>
            <Button
              className="w-full bg-primary hover:bg-primary/90"
              onClick={handleDeploy}
              disabled={!isComplete || saving}
            >
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Rocket className="h-4 w-4 mr-2" />}
              Deploy Event
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
