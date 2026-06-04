"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, Zap, Trophy, Users, Crown, UserPlus, Trash2 } from "lucide-react";
import TeamDetailModal from "@/components/ui/TeamDetailModal";
import { toast } from "sonner";
import {
  listTeams,
  autoFormTeams,
  createTeam,
  assignTeamMember,
  deleteTeam,
  listParticipants,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Team, Participant, TeamFormationConstraint } from "@/types";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Modal from "@/components/ui/Modal";

const inputBase: React.CSSProperties = {
  width: "100%",
  borderRadius: "0.5rem",
  border: "1px solid #222",
  background: "#0d0d0d",
  padding: "0.625rem 0.75rem",
  fontSize: "0.875rem",
  color: "#fff",
  outline: "none",
  fontFamily: "inherit",
  boxSizing: "border-box",
};

const ruleRow: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  fontSize: "0.85rem",
  color: "rgba(255,255,255,0.7)",
  flexWrap: "wrap",
};

export default function TeamsPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();

  const [teams, setTeams] = useState<Team[]>([]);
  const [teamModal, setTeamModal] = useState<Team | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoForming, setAutoForming] = useState(false);
  const [teamSize, setTeamSize] = useState(4);

  // Team-formation rules (constraints fed to the CP-SAT optimizer).
  const [avoidSameCollege, setAvoidSameCollege] = useState(false);
  const [genderDiversity, setGenderDiversity] = useState(false);
  const [genderMin, setGenderMin] = useState(1);
  const [balanceExperience, setBalanceExperience] = useState(false);
  const [requiredSkill, setRequiredSkill] = useState("");
  const [skillMinCount, setSkillMinCount] = useState(1);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");
  const [creating, setCreating] = useState(false);

  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assigningTeam, setAssigningTeam] = useState<Team | null>(null);
  const [selectedParticipant, setSelectedParticipant] = useState<string>("");
  const [isLeader, setIsLeader] = useState(false);
  const [assigning, setAssigning] = useState(false);

  const fetchAll = useCallback(() => {
    if (!id) return Promise.resolve();
    return Promise.all([
      listTeams(id),
      listParticipants(id).catch(() => []),
    ])
      .then(([t, p]) => {
        setTeams(t);
        setParticipants(p);
      })
      .catch((err: Error) => toast.error(err.message || "Failed to load teams"))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    fetchAll();
  }, [authLoading, user, fetchAll]);

  const assignedParticipantIds = new Set(
    teams.flatMap((t) => t.members?.map((m) => m.participant_id) ?? [])
  );
  const unassigned = participants.filter(
    (p) => !assignedParticipantIds.has(p.id)
  );

  const handleAutoForm = async () => {
    if (!id) return;
    const constraints: TeamFormationConstraint[] = [];
    if (avoidSameCollege) constraints.push({ type: "avoid_same_college" });
    if (genderDiversity) constraints.push({ type: "gender_diversity", min_per_team: genderMin });
    if (balanceExperience) constraints.push({ type: "balance_experience" });
    if (requiredSkill.trim()) constraints.push({ type: "required_skill", skill: requiredSkill.trim(), min_count: skillMinCount });
    setAutoForming(true);
    try {
      const result = await autoFormTeams(id, teamSize, constraints);
      if (result.success) {
        setTeams(result.teams);
        toast.success(result.message || `Formed ${result.teams.length} teams!`);
      } else {
        toast.error(result.message || "Auto-formation failed");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Auto-formation failed");
    } finally {
      setAutoForming(false);
    }
  };

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTeamName.trim() || !id) {
      toast.error("Team name is required");
      return;
    }
    setCreating(true);
    try {
      const team = await createTeam({ event_id: id, name: newTeamName });
      setTeams((prev) => [...prev, team]);
      setCreateModalOpen(false);
      setNewTeamName("");
      toast.success("Team created!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create team");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteTeam = async (teamId: string) => {
    if (!id || !window.confirm("Delete this team? This cannot be undone.")) return;
    try {
      await deleteTeam(id, teamId);
      setTeams((prev) => prev.filter((t) => t.id !== teamId));
      toast.success("Team deleted");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete team");
    }
  };

  const openAssignModal = (team: Team) => {
    setAssigningTeam(team);
    setSelectedParticipant("");
    setIsLeader(false);
    setAssignModalOpen(true);
  };

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assigningTeam || !selectedParticipant) {
      toast.error("Select a participant");
      return;
    }
    setAssigning(true);
    try {
      await assignTeamMember({
        team_id: assigningTeam.id,
        participant_id: selectedParticipant,
        is_leader: isLeader,
      });
      toast.success("Member assigned!");
      setAssignModalOpen(false);
      setLoading(true);
      fetchAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Assignment failed");
    } finally {
      setAssigning(false);
    }
  };

  const gridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: "1rem",
  };

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <div
        style={{
          marginBottom: "2rem",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#fff",
              margin: 0,
            }}
          >
            Teams
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            {teams.length} team{teams.length !== 1 ? "s" : ""} formed
            {unassigned.length > 0 && ` · ${unassigned.length} unassigned`}
          </p>
        </div>
        <Button variant="secondary" onClick={() => setCreateModalOpen(true)}>
          <Plus size={16} /> Create Team
        </Button>
      </div>

      <div
        style={{
          marginBottom: "2rem",
          borderRadius: "0.75rem",
          border: "1px solid rgba(232,80,58,0.2)",
          background: "rgba(232,80,58,0.05)",
          padding: "1.25rem",
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
          }}
        >
          <div>
            <h3
              style={{
                fontSize: "1rem",
                fontWeight: 600,
                color: "#fff",
                margin: 0,
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <Zap size={16} color="#e8503a" />
              Auto-Form Teams
            </h3>
            <p
              style={{
                marginTop: "0.25rem",
                fontSize: "0.875rem",
                color: "rgba(255,255,255,0.5)",
              }}
            >
              Automatically group participants into balanced teams.
            </p>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              flexWrap: "wrap",
            }}
          >
            <label
              style={{
                fontSize: "0.875rem",
                color: "rgba(255,255,255,0.6)",
                whiteSpace: "nowrap",
              }}
            >
              Team size:
            </label>
            <input
              type="number"
              value={teamSize}
              onChange={(e) => setTeamSize(parseInt(e.target.value) || 4)}
              min={2}
              max={20}
              style={{ ...inputBase, width: "4rem", textAlign: "center" }}
            />
            <Button
              variant="primary"
              loading={autoForming}
              onClick={handleAutoForm}
            >
              <Zap size={16} /> Auto-Form
            </Button>
          </div>
        </div>

        {/* Formation rules → CP-SAT constraints */}
        <div
          style={{
            marginTop: "1rem",
            paddingTop: "1rem",
            borderTop: "1px solid rgba(232,80,58,0.15)",
          }}
        >
          <p
            style={{
              fontSize: "0.72rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "rgba(255,255,255,0.4)",
              margin: "0 0 0.6rem",
            }}
          >
            Formation rules
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem" }}>
            <label style={ruleRow}>
              <input type="checkbox" checked={avoidSameCollege} onChange={(e) => setAvoidSameCollege(e.target.checked)} />
              <span>Avoid grouping members from the same institution</span>
            </label>

            <label style={ruleRow}>
              <input type="checkbox" checked={balanceExperience} onChange={(e) => setBalanceExperience(e.target.checked)} />
              <span>Balance experience levels across teams</span>
            </label>

            <div style={ruleRow}>
              <input type="checkbox" checked={genderDiversity} onChange={(e) => setGenderDiversity(e.target.checked)} />
              <span>Ensure at least</span>
              <input
                type="number" min={1} max={teamSize} value={genderMin}
                disabled={!genderDiversity}
                onChange={(e) => setGenderMin(Math.max(1, parseInt(e.target.value) || 1))}
                style={{ ...inputBase, width: "3.25rem", textAlign: "center", opacity: genderDiversity ? 1 : 0.4 }}
              />
              <span>female member(s) per team</span>
            </div>

            <div style={ruleRow}>
              <input
                type="checkbox" checked={!!requiredSkill.trim()}
                onChange={(e) => { if (!e.target.checked) setRequiredSkill(""); }}
                readOnly={!requiredSkill.trim()}
              />
              <span>Require at least</span>
              <input
                type="number" min={1} max={teamSize} value={skillMinCount}
                onChange={(e) => setSkillMinCount(Math.max(1, parseInt(e.target.value) || 1))}
                style={{ ...inputBase, width: "3.25rem", textAlign: "center" }}
              />
              <span>member(s) with skill</span>
              <input
                type="text" value={requiredSkill} placeholder="e.g. Python"
                onChange={(e) => setRequiredSkill(e.target.value)}
                style={{ ...inputBase, width: "9rem" }}
              />
            </div>
          </div>
          <p style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.3)", margin: "0.6rem 0 0" }}>
            Rules are best-effort — the optimizer satisfies them where the participant pool allows.
          </p>
        </div>
      </div>

      {loading ? (
        <div style={gridStyle}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "10rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : teams.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1rem",
            padding: "5rem 0",
            textAlign: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              height: "4rem",
              width: "4rem",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "1rem",
              background: "#111",
              border: "1px solid #222",
            }}
          >
            <Trophy size={32} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>
            No teams yet. Use Auto-Form or create manually.
          </p>
        </div>
      ) : (
        <div style={gridStyle}>
          {teams.map((team, i) => (
            <motion.div
              key={team.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05 }}
              style={{
                borderRadius: "0.75rem",
                border: "1px solid #222",
                background: "#111",
                padding: "1.25rem",
              }}
            >
              <div
                style={{
                  marginBottom: "1rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "0.75rem",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    minWidth: 0,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      height: "2.5rem",
                      width: "2.5rem",
                      flexShrink: 0,
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: "0.75rem",
                      background: "rgba(232,80,58,0.15)",
                      color: "#e8503a",
                    }}
                  >
                    <Trophy size={20} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <button
                      onClick={() => setTeamModal(team)}
                      style={{
                        background: "transparent", border: "none", cursor: "pointer",
                        padding: 0, textAlign: "left",
                        fontWeight: 700, color: "#fff", fontSize: "1rem",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        maxWidth: "100%",
                        textDecoration: "underline", textDecorationColor: "rgba(255,255,255,0.15)",
                        textUnderlineOffset: "3px", transition: "color 0.15s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "#e8503a")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "#fff")}
                    >
                      {team.name}
                    </button>
                    <p
                      style={{
                        fontSize: "0.75rem",
                        color: "rgba(255,255,255,0.4)",
                        margin: 0,
                      }}
                    >
                      {team.members?.length || 0} member
                      {(team.members?.length || 0) !== 1 ? "s" : ""}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "0.375rem", flexShrink: 0 }}>
                  <button
                    onClick={() => openAssignModal(team)}
                    title="Add member"
                    style={{
                      display: "flex",
                      height: "2rem",
                      width: "2rem",
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: "0.5rem",
                      border: "1px solid #222",
                      color: "rgba(255,255,255,0.3)",
                      background: "transparent",
                      cursor: "pointer",
                    }}
                  >
                    <UserPlus size={14} />
                  </button>
                  <button
                    onClick={() => handleDeleteTeam(team.id)}
                    title="Delete team"
                    style={{
                      display: "flex",
                      height: "2rem",
                      width: "2rem",
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: "0.5rem",
                      border: "1px solid #222",
                      color: "rgba(255,255,255,0.2)",
                      background: "transparent",
                      cursor: "pointer",
                      transition: "color 0.2s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "#f87171")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(255,255,255,0.2)")}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {team.members && team.members.length > 0 ? (
                <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
                  {team.members.map((member) => (
                    <li
                      key={member.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        fontSize: "0.875rem",
                        padding: "0.25rem 0",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          height: "1.5rem",
                          width: "1.5rem",
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: "9999px",
                          background: "rgba(255,255,255,0.05)",
                          color: "rgba(255,255,255,0.4)",
                        }}
                      >
                        <Users size={12} />
                      </div>
                      <span
                        style={{
                          color: "rgba(255,255,255,0.7)",
                          flex: 1,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {member.participant?.name ||
                          `Participant ${String(member.participant_id).slice(0, 8)}`}
                      </span>
                      {member.is_leader && (
                        <Crown
                          size={14}
                          color="#facc15"
                          style={{ flexShrink: 0 }}
                        />
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.3)",
                    fontStyle: "italic",
                    margin: 0,
                  }}
                >
                  No members yet
                </p>
              )}
            </motion.div>
          ))}
        </div>
      )}

      <Modal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create Team"
      >
        <form
          onSubmit={handleCreateTeam}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <Input
            label="Team Name *"
            value={newTeamName}
            onChange={(e) => setNewTeamName(e.target.value)}
            placeholder="e.g., Team Alpha"
            fullWidth
            required
          />
          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={creating}
              style={{ flex: 1 }}
            >
              Create
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={assignModalOpen}
        onClose={() => setAssignModalOpen(false)}
        title={`Add Member to ${assigningTeam?.name ?? "Team"}`}
      >
        <form
          onSubmit={handleAssign}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <div>
            <label
              style={{
                display: "block",
                marginBottom: "0.375rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "rgba(255,255,255,0.7)",
              }}
            >
              Participant *
            </label>
            {unassigned.length === 0 ? (
              <p
                style={{
                  ...inputBase,
                  color: "rgba(255,255,255,0.3)",
                  margin: 0,
                }}
              >
                All participants are already assigned to teams.
              </p>
            ) : (
              <select
                value={selectedParticipant}
                onChange={(e) => setSelectedParticipant(e.target.value)}
                required
                style={inputBase}
              >
                <option value="">Select a participant...</option>
                {unassigned.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name || p.email}
                    {p.skills && p.skills.length > 0
                      ? ` — ${p.skills.join(", ")}`
                      : ""}
                  </option>
                ))}
              </select>
            )}
          </div>

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={isLeader}
              onChange={(e) => setIsLeader(e.target.checked)}
              style={{ height: "1rem", width: "1rem", accentColor: "#e8503a" }}
            />
            <span
              style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.7)" }}
            >
              Set as team leader{" "}
              <Crown
                size={14}
                color="#facc15"
                style={{
                  display: "inline",
                  verticalAlign: "middle",
                  marginLeft: "0.25rem",
                }}
              />
            </span>
          </label>

          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setAssignModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={assigning}
              disabled={unassigned.length === 0}
              style={{ flex: 1 }}
            >
              <UserPlus size={16} /> Assign
            </Button>
          </div>
        </form>
      </Modal>

      {teamModal && id && (
        <TeamDetailModal
          open={!!teamModal}
          onClose={() => setTeamModal(null)}
          eventId={id}
          teamId={teamModal.id}
          teamName={teamModal.name}
          initialTeam={teamModal}
        />
      )}
    </div>
  );
}
