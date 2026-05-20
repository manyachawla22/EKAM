"use client";
import { useState } from "react";
import { mockParticipants } from "@/lib/mock-data";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Search, Download, LayoutGrid, LayoutList, Users, Filter, ChevronUp, ChevronDown } from "lucide-react";
import type { Participant } from "@/lib/mock-data";

const statusColors: Record<string, string> = {
  confirmed: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  pending: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  waitlisted: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  rejected: "bg-red-500/10 text-red-500 border-red-500/20",
};

export default function ParticipantsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");
  const [selectedParticipant, setSelectedParticipant] = useState<Participant | null>(null);
  const [sortField, setSortField] = useState<"name" | "atsScore">("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const filtered = mockParticipants
    .filter((p) => {
      const matchSearch = p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.email.toLowerCase().includes(search.toLowerCase()) ||
        p.institution.toLowerCase().includes(search.toLowerCase());
      const matchStatus = statusFilter === "all" || p.registrationStatus === statusFilter;
      return matchSearch && matchStatus;
    })
    .sort((a, b) => {
      const mult = sortDir === "asc" ? 1 : -1;
      if (sortField === "name") return a.name.localeCompare(b.name) * mult;
      return (a.atsScore - b.atsScore) * mult;
    });

  const toggleSort = (field: "name" | "atsScore") => {
    if (sortField === field) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("asc"); }
  };

  const SortIcon = ({ field }: { field: "name" | "atsScore" }) => (
    sortField === field ? (sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />) : null
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Participants</h1>
          <p className="text-sm text-muted-foreground">{filtered.length} of {mockParticipants.length} participants</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => toast.success("Exported 20 participants to CSV")}>
            <Download className="h-3.5 w-3.5 mr-1.5" />Export
          </Button>
          <Button variant="outline" size="sm" onClick={() => toast.info("Bulk action: 3 participants selected")}>
            Bulk Actions
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
        <CardContent className="p-4 flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search by name, email, or institution..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
          </div>
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v ?? "all")}>
            <SelectTrigger className="w-40"><Filter className="h-3.5 w-3.5 mr-2" /><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="confirmed">Confirmed</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="waitlisted">Waitlisted</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex border border-border rounded-lg overflow-hidden">
            <button onClick={() => setViewMode("table")} className={`p-2 ${viewMode === "table" ? "bg-primary/10 text-primary" : "text-muted-foreground"}`}>
              <LayoutList className="h-4 w-4" />
            </button>
            <button onClick={() => setViewMode("cards")} className={`p-2 ${viewMode === "cards" ? "bg-primary/10 text-primary" : "text-muted-foreground"}`}>
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Table View */}
      {viewMode === "table" ? (
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="cursor-pointer" onClick={() => toggleSort("name")}>
                    <span className="flex items-center gap-1">Name <SortIcon field="name" /></span>
                  </TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead className="hidden md:table-cell">Institution</TableHead>
                  <TableHead className="hidden lg:table-cell">Skills</TableHead>
                  <TableHead>Team</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="cursor-pointer" onClick={() => toggleSort("atsScore")}>
                    <span className="flex items-center gap-1">ATS <SortIcon field="atsScore" /></span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p, i) => (
                  <TableRow key={p.id} className="cursor-pointer hover:bg-muted/30" onClick={() => setSelectedParticipant(p)}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Avatar className="h-7 w-7">
                          <AvatarFallback className="text-[10px] bg-primary/10 text-primary">{p.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback>
                        </Avatar>
                        <span className="font-medium text-sm">{p.name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{p.email}</TableCell>
                    <TableCell className="hidden md:table-cell text-xs">{p.institution}</TableCell>
                    <TableCell className="hidden lg:table-cell">
                      <div className="flex gap-1 flex-wrap">
                        {p.skills.slice(0, 2).map((s) => <Badge key={s} variant="outline" className="text-[9px] px-1.5 py-0">{s}</Badge>)}
                        {p.skills.length > 2 && <span className="text-[9px] text-muted-foreground">+{p.skills.length - 2}</span>}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs">{p.team}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={`text-[10px] ${statusColors[p.registrationStatus]}`}>{p.registrationStatus}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={p.atsScore} className="h-1.5 w-12" />
                        <span className="text-xs font-medium">{p.atsScore}</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        /* Cards View */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((p, i) => (
            <motion.div key={p.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
              <Card className="border-border/50 bg-card/80 backdrop-blur-sm cursor-pointer hover:border-primary/30 transition-all" onClick={() => setSelectedParticipant(p)}>
                <CardContent className="p-4 text-center">
                  <Avatar className="h-12 w-12 mx-auto mb-3">
                    <AvatarFallback className="bg-primary/10 text-primary font-semibold">{p.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback>
                  </Avatar>
                  <p className="font-semibold text-sm">{p.name}</p>
                  <p className="text-xs text-muted-foreground">{p.institution}</p>
                  <div className="flex gap-1 justify-center mt-2 flex-wrap">
                    {p.skills.map((s) => <Badge key={s} variant="outline" className="text-[9px] px-1.5 py-0">{s}</Badge>)}
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <Badge variant="outline" className={`text-[10px] ${statusColors[p.registrationStatus]}`}>{p.registrationStatus}</Badge>
                    <span className="text-xs font-medium">ATS: {p.atsScore}</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Profile Drawer */}
      <Sheet open={!!selectedParticipant} onOpenChange={(open) => !open && setSelectedParticipant(null)}>
        <SheetContent className="w-full sm:max-w-md">
          {selectedParticipant && (
            <div className="space-y-6 mt-6">
              <SheetHeader>
                <div className="flex items-center gap-3">
                  <Avatar className="h-14 w-14">
                    <AvatarFallback className="bg-primary/10 text-primary text-lg font-semibold">{selectedParticipant.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback>
                  </Avatar>
                  <div>
                    <SheetTitle>{selectedParticipant.name}</SheetTitle>
                    <p className="text-sm text-muted-foreground">{selectedParticipant.email}</p>
                  </div>
                </div>
              </SheetHeader>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: "Phone", value: selectedParticipant.phone },
                  { label: "Institution", value: selectedParticipant.institution },
                  { label: "Gender", value: selectedParticipant.gender },
                  { label: "Age", value: selectedParticipant.age },
                  { label: "Team", value: selectedParticipant.team },
                  { label: "Stage", value: selectedParticipant.stage },
                ].map((item) => (
                  <div key={item.label}>
                    <p className="text-xs text-muted-foreground">{item.label}</p>
                    <p className="text-sm font-medium">{item.value}</p>
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-2">Skills</p>
                <div className="flex gap-1.5 flex-wrap">
                  {selectedParticipant.skills.map((s) => <Badge key={s} variant="outline">{s}</Badge>)}
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-2">ATS Score</p>
                <div className="flex items-center gap-3">
                  <Progress value={selectedParticipant.atsScore} className="flex-1 h-2" />
                  <span className="font-bold text-lg">{selectedParticipant.atsScore}</span>
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Status</p>
                <Badge variant="outline" className={statusColors[selectedParticipant.registrationStatus]}>
                  {selectedParticipant.registrationStatus}
                </Badge>
              </div>
              {selectedParticipant.notes && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Notes</p>
                  <p className="text-sm">{selectedParticipant.notes}</p>
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
