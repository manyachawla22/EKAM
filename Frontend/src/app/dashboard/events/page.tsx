"use client";
import { mockEvents } from "@/lib/mock-data";
import { EventCard } from "@/components/event-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useState, useEffect } from "react";
import { Plus, Search, Filter } from "lucide-react";
import Link from "next/link";
import { aiApi } from "@/lib/api";
import type { Event, EventStage, Round } from "@/lib/mock-data";

export function mapApiConfigToEvent(api: Record<string, any>): Event {
  const phase: string = api.status?.current_phase || "draft";
  const phases = ["draft", "ready", "registration_open", "registration_closed", "in_progress", "judging", "completed", "archived"];
  const phaseIdx = phases.indexOf(phase);
  const progress = phaseIdx <= 0 ? 5 : Math.round((phaseIdx / (phases.length - 1)) * 100);

  const apiRounds: any[] = Array.isArray(api.rounds) ? api.rounds : [];
  const rounds: Round[] = apiRounds.map((r: any, i: number) => ({
    id: r.round_id || `r${i + 1}`,
    name: r.round_name || `Round ${i + 1}`,
    status: "upcoming" as const,
    startDate: r.dates?.starts_at?.slice(0, 10) || "",
    endDate: r.dates?.ends_at?.slice(0, 10) || "",
    participantsAdvanced: 0,
    totalParticipants: api.participants?.capacity?.max_participants || 0,
  }));

  const stages: EventStage[] = [
    { id: "s1", name: "Registration", status: "upcoming", owner: "Organizer", completionPct: 0, lastUpdated: "-", description: "Open registration and collect participant details" },
    ...apiRounds.map((r: any, i: number) => ({
      id: `s${i + 2}`,
      name: r.round_name || `Round ${i + 1}`,
      status: "upcoming" as const,
      owner: "Participant",
      completionPct: 0,
      lastUpdated: "-",
      description: r.description || "",
    })),
    { id: `s${apiRounds.length + 2}`, name: "Results", status: "upcoming", owner: "Organizer", completionPct: 0, lastUpdated: "-", description: "Winner announcement and prizes" },
  ];

  return {
    id: api.event_id || api.id || "",
    hash: api.hash || "",
    name: api.core?.name || api.name || "Untitled Event",
    type: api.core?.event_type || "hackathon",
    status: phase === "completed" || phase === "archived" ? "completed" : phase === "draft" ? "draft" : "active",
    stage: phase.replace(/_/g, " "),
    participantCount: 0,
    judgeCount: (api.judging_panel?.judges || []).length,
    teamCount: 0,
    maxParticipants: api.participants?.capacity?.max_participants || 0,
    approvalStatus: "pending",
    progress,
    createdAt: api.status?.created_at?.slice(0, 10) || new Date().toISOString().slice(0, 10),
    updatedAt: api.status?.updated_at?.slice(0, 10) || new Date().toISOString().slice(0, 10),
    description: api.core?.description || "",
    stages,
    rounds,
  };
}

export default function EventsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [deployedEvents, setDeployedEvents] = useState<Event[]>([]);

  useEffect(() => {
    aiApi.getDeployedEvents()
      .then((data: any[]) => setDeployedEvents(data.map(mapApiConfigToEvent)))
      .catch(() => {});
  }, []);

  const allEvents = [...deployedEvents, ...mockEvents];

  const filtered = allEvents.filter((e) => {
    const matchSearch = e.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || e.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Events</h1>
          <p className="text-sm text-muted-foreground">{filtered.length} events found</p>
        </div>
        <Button render={<Link href="/dashboard/create" />} className="bg-primary hover:bg-primary/90">
          <Plus className="h-4 w-4 mr-2" />Create Event
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search events..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v ?? "all")}>
          <SelectTrigger className="w-40"><Filter className="h-3.5 w-3.5 mr-2" /><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((event, i) => (
          <EventCard key={event.id} event={event} index={i} />
        ))}
      </div>
    </div>
  );
}
