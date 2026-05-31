import { auth } from "./firebase";
import type {
  User,
  Event,
  Round,
  Participant,
  Team,
  TeamMember,
  Judge,
  JudgeAssignment,
  ApprovalRequest,
  ApprovalActionBody,
  Notification,
  Anomaly,
  Submission,
  Evaluation,
  Report,
  AIChatMessage,
  AIChatResponse,
  AIDeployResponse,
  EventConfig,
  LoginBody,
  CreateEventBody,
  UpdateEventBody,
  CreateRoundBody,
  RegisterParticipantBody,
  CreateTeamBody,
  AssignTeamMemberBody,
  UploadSubmissionBody,
  SubmitEvaluationBody,
  AssignJudgeBody,
  InviteJudgeBody,
  GenerateReportBody,
  AutoFormTeamsResponse,
  UserRole,
} from "@/types";

export const API_BASE = "http://localhost:8000/api/v1";

// ─── EKAM JWT storage ────────────────────────────────────────────────────────
// After /auth/firebase-login the backend returns a TokenResponse. We persist
// it here and prefer it over the Firebase ID token for every subsequent
// request. This avoids hammering Google's certificate endpoint on every API
// call, which is the cause of the random "Invalid Firebase credentials:
// ConnectionResetError" failures.

const EKAM_TOKEN_KEY = "ekam:access-token";

export function setEkamToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) sessionStorage.setItem(EKAM_TOKEN_KEY, token);
  else sessionStorage.removeItem(EKAM_TOKEN_KEY);
}

export function getEkamToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(EKAM_TOKEN_KEY);
}

// ─── Auth Headers ─────────────────────────────────────────────────────────────

export async function getAuthHeaders(): Promise<HeadersInit> {
  // Prefer the EKAM JWT (issued locally by the backend) over the Firebase
  // ID token. The Firebase token is only used to obtain the JWT during the
  // initial login call.
  const ekam = getEkamToken();
  if (ekam) {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ekam}`,
    };
  }
  const user = auth.currentUser;
  if (!user) {
    return { "Content-Type": "application/json" };
  }
  try {
    const token = await user.getIdToken();
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  } catch {
    return { "Content-Type": "application/json" };
  }
}

// ─── Generic Fetch Helper ─────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let errorMessage = `API Error: ${response.status}`;
    try {
      const errorData = (await response.json()) as {
        detail?: unknown;
      };
      // FastAPI returns `detail` as a string for HTTPException but as an
      // array of {loc, msg, type, ...} objects for 422 validation errors.
      // Without this normalization the UI shows "[object Object]".
      const d = errorData.detail;
      if (typeof d === "string") {
        errorMessage = d;
      } else if (Array.isArray(d)) {
        errorMessage = d
          .map((item) => {
            if (item && typeof item === "object") {
              const obj = item as { loc?: unknown; msg?: string };
              const loc = Array.isArray(obj.loc)
                ? obj.loc.filter((x) => x !== "body").join(".")
                : "";
              return loc ? `${loc}: ${obj.msg || ""}` : obj.msg || JSON.stringify(item);
            }
            return String(item);
          })
          .join("; ");
      } else if (d && typeof d === "object") {
        errorMessage = JSON.stringify(d);
      }
    } catch {
      // body wasn't JSON — keep the default message
    }
    throw new Error(`${errorMessage} (${response.status})`);
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

// ─── AUTH ─────────────────────────────────────────────────────────────────────

// ─── Participant / Judge token response shape ─────────────────────────────────
export interface OtpTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  actor_type: "participant" | "judge";
  event_id: string;
  session_id: string;
}

// Request OTP for a participant or judge (Step 1 of OTP login)
export async function requestOtpAccess(
  email: string,
  eventHash: string
): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/auth/request-access", {
    method: "POST",
    body: JSON.stringify({ email, event_hash: eventHash }),
  });
}

// Verify OTP and receive EKAM JWT (Step 2 of OTP login)
export async function verifyOtpAccess(
  email: string,
  eventHash: string,
  otp: string
): Promise<OtpTokenResponse> {
  const resp = await apiFetch<OtpTokenResponse>("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({ email, event_hash: eventHash, otp }),
  });
  if (resp?.access_token) {
    setEkamToken(resp.access_token);
  }
  return resp;
}

// Verify magic link token and receive EKAM JWT
export async function verifyMagicLink(token: string): Promise<OtpTokenResponse> {
  const resp = await apiFetch<OtpTokenResponse>("/auth/magic-login", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
  if (resp?.access_token) {
    setEkamToken(resp.access_token);
  }
  return resp;
}

// New backend (post PR #7):
// - /auth/login was removed. Organizer/Admin sign in with their Firebase ID
//   token via /auth/firebase-login. The backend issues an EKAM JWT in the
//   response but the Firebase token also keeps working for subsequent
//   requests, so we don't have to swap tokens for now.
// - /auth/me now returns { id, actor_type, event_id, profile, permissions,
//   is_event_scoped } instead of a flat User. Unwrap `profile` here so callers
//   keep seeing a User shape.
export async function loginUser(body: LoginBody): Promise<User> {
  // Force the Firebase ID token (not a stale EKAM JWT) on this one call so
  // the backend can authenticate via Firebase and re-issue a fresh session.
  setEkamToken(null);

  // /auth/login accepts an optional { name, role } body:
  //   - On signup we want to pass the user's chosen role.
  //   - On regular login we leave them omitted and the backend keeps the
  //     existing user's role unchanged.
  const payload: Record<string, string | undefined> = {};
  if (body?.name) payload.name = body.name;
  if (body?.role) payload.role = body.role;

  const resp = await apiFetch<{
    access_token: string;
    refresh_token?: string;
    token_type?: string;
    actor_type?: string;
    name?: string;
    email?: string;
    role?: string;
    organization?: string | null;
  }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  // Persist the JWT so all subsequent requests go through the local
  // backend and skip the Google round-trip.
  if (resp?.access_token) {
    setEkamToken(resp.access_token);
  }

  // The /auth/login response includes the profile fields directly, so we
  // can return a User without a second round-trip to /auth/me.
  return getMe();
}

export async function getMe(): Promise<User> {
  const raw = await apiFetch<{
    id: string;
    actor_type: string;
    event_id?: string | null;
    profile: User;
    permissions?: string[];
    is_event_scoped?: boolean;
  }>("/auth/me");
  // Map the wrapped MeResponse back to a flat User the rest of the app
  // expects (role from actor_type when profile doesn't carry it).
  return {
    ...raw.profile,
    role: (raw.profile?.role ?? raw.actor_type) as User["role"],
  };
}

// ─── EVENTS ───────────────────────────────────────────────────────────────────

export async function createEvent(body: CreateEventBody): Promise<Event> {
  return apiFetch<Event>("/events/create", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listEvents(): Promise<Event[]> {
  return apiFetch<Event[]>("/events");
}

export async function getEvent(id: string): Promise<Event> {
  return apiFetch<Event>(`/events/${id}`);
}

export async function updateEvent(
  id: string,
  body: UpdateEventBody
): Promise<Event> {
  return apiFetch<Event>(`/events/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteEvent(id: string): Promise<void> {
  return apiFetch<void>(`/events/${id}`, {
    method: "DELETE",
  });
}

// ─── ROUNDS ───────────────────────────────────────────────────────────────────

export async function createRound(body: CreateRoundBody): Promise<Round> {
  return apiFetch<Round>("/rounds/create", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listRounds(eventId: string): Promise<Round[]> {
  return apiFetch<Round[]>(`/rounds/${eventId}`);
}

// ─── PARTICIPANTS ─────────────────────────────────────────────────────────────

export async function registerParticipant(
  body: RegisterParticipantBody
): Promise<Participant> {
  return apiFetch<Participant>("/participants/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listParticipants(eventId: string): Promise<Participant[]> {
  return apiFetch<Participant[]>(`/participants/${eventId}`);
}

// ─── TEAMS ────────────────────────────────────────────────────────────────────

export async function createTeam(body: CreateTeamBody): Promise<Team> {
  return apiFetch<Team>("/teams/create", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function assignTeamMember(
  body: AssignTeamMemberBody
): Promise<TeamMember> {
  // Moved to the assignments router in PR #7.
  return apiFetch<TeamMember>("/assignments/team-member", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listTeams(eventId: string): Promise<Team[]> {
  return apiFetch<Team[]>(`/teams/${eventId}`);
}

export async function autoFormTeams(
  eventId: string,
  teamSize: number = 4
): Promise<AutoFormTeamsResponse> {
  // URL moved from /teams/auto-form/{eventId} to /teams/{eventId}/auto-form in
  // PR #7. The endpoint now creates an ApprovalRequest instead of committing
  // teams directly, so the response shape is different — we wrap it back into
  // the legacy AutoFormTeamsResponse shape so the existing UI still works.
  const raw = await apiFetch<{ message: string; approval_id: string }>(
    `/teams/${eventId}/auto-form?team_size=${teamSize}`,
    { method: "POST" }
  );
  return {
    success: true,
    teams: [],
    leftovers: [],
    message: `${raw.message} Approval ID: ${raw.approval_id}`,
  };
}

// ─── SUBMISSIONS ──────────────────────────────────────────────────────────────

export async function uploadSubmission(
  body: UploadSubmissionBody
): Promise<Submission> {
  return apiFetch<Submission>("/submissions/upload", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listSubmissions(roundId: string): Promise<Submission[]> {
  return apiFetch<Submission[]>(`/submissions/${roundId}`);
}

// ─── EVALUATIONS ──────────────────────────────────────────────────────────────

export async function submitEvaluation(
  body: SubmitEvaluationBody
): Promise<Evaluation> {
  return apiFetch<Evaluation>("/evaluations/submit", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getEvaluations(
  submissionId: string
): Promise<Evaluation[]> {
  return apiFetch<Evaluation[]>(`/evaluations/${submissionId}`);
}

// ─── JUDGES ───────────────────────────────────────────────────────────────────

export async function assignJudge(body: AssignJudgeBody): Promise<JudgeAssignment> {
  return apiFetch<JudgeAssignment>("/judges/assign", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function inviteJudge(body: InviteJudgeBody): Promise<Judge> {
  // Backend has no /judges/invite-judge endpoint; we use /judges/create with
  // the same payload. "Invitation" semantics (sending a join email) aren't
  // implemented backend-side — the judge row is created directly.
  return apiFetch<Judge>("/judges/create", {
    method: "POST",
    body: JSON.stringify({
      name: body.name || body.email.split("@")[0],
      email: body.email,
      event_id: body.event_id,
      institution: body.institution,
      expertise: body.expertise || [],
    }),
  });
}

export async function listJudges(eventId: string): Promise<Judge[]> {
  return apiFetch<Judge[]>(`/judges/${eventId}`);
}

export interface JudgeAssignmentDetail {
  assignment_id: string;
  round_id: string;
  round_name: string;
  round_status: string;
  team_id: string;
  team_name: string;
  submission_id: string | null;
  submission_status: string | null;
  already_evaluated: boolean;
}

export interface JudgeInviteDetail {
  judge_name: string;
  judge_email: string;
  event_name: string;
  event_hash: string;
  invite_status: "pending" | "accepted" | "declined";
}

export async function getJudgeAssignments(
  eventId: string,
  judgeId: string
): Promise<JudgeAssignmentDetail[]> {
  return apiFetch<JudgeAssignmentDetail[]>(`/judges/${eventId}/${judgeId}/assignments`);
}

export async function getJudgeInvite(token: string): Promise<JudgeInviteDetail> {
  return apiFetch<JudgeInviteDetail>(`/judges/invite/${token}`);
}

export async function respondJudgeInvite(
  token: string,
  accepted: boolean
): Promise<JudgeInviteDetail> {
  return apiFetch<JudgeInviteDetail>("/judges/invite/respond", {
    method: "POST",
    body: JSON.stringify({ token, accepted }),
  });
}

export async function listRoundJudges(roundId: string): Promise<JudgeAssignment[]> {
  return apiFetch<JudgeAssignment[]>(`/judges/round/${roundId}`);
}

export async function autoAssignJudges(
  roundId: string,
  judgesPerTeam: number = 2
): Promise<{ success: boolean; assignments: JudgeAssignment[] }> {
  return apiFetch<{ success: boolean; assignments: JudgeAssignment[] }>(
    `/judges/auto-assign/${roundId}?judges_per_team=${judgesPerTeam}`,
    { method: "POST" }
  );
}

// ─── REPORTS ─────────────────────────────────────────────────────────────────

export async function generateReport(body: GenerateReportBody): Promise<Report> {
  return apiFetch<Report>("/reports/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listReports(eventId: string): Promise<Report[]> {
  return apiFetch<Report[]>(`/reports/${eventId}`);
}

// ─── AI ───────────────────────────────────────────────────────────────────────

export async function aiChat(
  messages: AIChatMessage[],
  eventId?: string,
  eventConfig?: EventConfig
): Promise<AIChatResponse> {
  return apiFetch<AIChatResponse>("/ai/chat", {
    method: "POST",
    body: JSON.stringify({ messages, event_id: eventId, event_config: eventConfig }),
  });
}

export async function aiDeploy(
  eventConfig: EventConfig,
  eventId?: string
): Promise<AIDeployResponse> {
  return apiFetch<AIDeployResponse>("/ai/deploy", {
    method: "POST",
    body: JSON.stringify({ event_config: eventConfig, event_id: eventId }),
  });
}

export async function listAIEvents(): Promise<Event[]> {
  return apiFetch<Event[]>("/ai/events");
}

export async function getAIEvent(hash: string): Promise<EventConfig> {
  return apiFetch<EventConfig>(`/ai/events/${hash}`);
}

// ─── APPROVALS ────────────────────────────────────────────────────────────────

export async function listPendingApprovals(
  eventId: string
): Promise<ApprovalRequest[]> {
  return apiFetch<ApprovalRequest[]>(`/approvals/${eventId}`);
}

export async function listApprovalHistory(
  eventId: string
): Promise<ApprovalRequest[]> {
  return apiFetch<ApprovalRequest[]>(`/approvals/${eventId}/history`);
}

export async function getApproval(
  eventId: string,
  approvalId: string
): Promise<ApprovalRequest> {
  return apiFetch<ApprovalRequest>(`/approvals/${eventId}/${approvalId}`);
}

export async function reviewApproval(
  eventId: string,
  approvalId: string,
  body: ApprovalActionBody
): Promise<ApprovalRequest> {
  return apiFetch<ApprovalRequest>(
    `/approvals/${eventId}/${approvalId}/review`,
    {
      method: "POST",
      body: JSON.stringify(body),
    }
  );
}

// ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

export async function listMyNotifications(
  unreadOnly: boolean = false
): Promise<Notification[]> {
  return apiFetch<Notification[]>(
    `/notifications${unreadOnly ? "?unread_only=true" : ""}`
  );
}

export async function markNotificationRead(
  notificationId: string
): Promise<{ message?: string }> {
  return apiFetch<{ message?: string }>(
    `/notifications/${notificationId}/read`,
    { method: "POST" }
  );
}

// ─── ANOMALIES ────────────────────────────────────────────────────────────────

export async function listAnomalies(eventId: string): Promise<Anomaly[]> {
  return apiFetch<Anomaly[]>(`/anomalies/${eventId}`);
}

export async function resolveAnomaly(
  eventId: string,
  anomalyId: string
): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(
    `/anomalies/${eventId}/${anomalyId}/resolve`,
    { method: "POST" }
  );
}

// ─── DELETE OPERATIONS ───────────────────────────────────────────────────────

export async function deleteParticipant(
  eventId: string,
  participantId: string
): Promise<void> {
  return apiFetch<void>(`/participants/${eventId}/${participantId}`, {
    method: "DELETE",
  });
}

export async function deleteJudge(
  eventId: string,
  judgeId: string
): Promise<void> {
  return apiFetch<void>(`/judges/${eventId}/${judgeId}`, {
    method: "DELETE",
  });
}

export async function deleteTeam(
  eventId: string,
  teamId: string
): Promise<void> {
  return apiFetch<void>(`/teams/${eventId}/${teamId}`, {
    method: "DELETE",
  });
}

export async function deleteRound(
  eventId: string,
  roundId: string
): Promise<void> {
  return apiFetch<void>(`/rounds/${eventId}/${roundId}`, {
    method: "DELETE",
  });
}

// ─── BULK CSV IMPORT ──────────────────────────────────────────────────────────

async function uploadCsv<T>(path: string, file: File): Promise<T> {
  // The auth header needs to come from getAuthHeaders, but we must NOT set
  // Content-Type — the browser sets the multipart boundary itself.
  const headers = await getAuthHeaders();
  const cleaned: Record<string, string> = {};
  for (const [k, v] of Object.entries(headers as Record<string, string>)) {
    if (k.toLowerCase() !== "content-type") cleaned[k] = v;
  }
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: cleaned,
    body: form,
  });
  if (!response.ok) {
    let msg = `Upload failed: ${response.status}`;
    try {
      const errData = (await response.json()) as { detail?: unknown };
      const d = errData.detail;
      if (typeof d === "string") msg = d;
      else if (d) msg = JSON.stringify(d);
    } catch {
      // body wasn't JSON
    }
    throw new Error(msg);
  }
  return response.json() as Promise<T>;
}

export async function uploadParticipantsCsv(
  eventId: string,
  file: File
): Promise<{ message: string; count: number }> {
  return uploadCsv(`/participants/${eventId}/upload-csv`, file);
}

export async function uploadJudgesCsv(
  eventId: string,
  file: File
): Promise<{ message: string; count: number }> {
  return uploadCsv(`/judges/${eventId}/upload-csv`, file);
}

// ─── Utility ─────────────────────────────────────────────────────────────────

export function generateHash(): string {
  return Math.random().toString(36).substring(2, 10) +
    Math.random().toString(36).substring(2, 10);
}

export function getRoleDashboard(role: UserRole): string {
  switch (role) {
    case "organizer":
      return "/organizer/events";
    case "participant":
      return "/participant/events";
    case "judge":
      return "/judge/assignments";
    case "admin":
      return "/organizer/events";
    default:
      return "/dashboard";
  }
}
