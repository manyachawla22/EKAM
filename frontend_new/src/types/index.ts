// ─── Enums ────────────────────────────────────────────────────────────────────

export type UserRole = "organizer" | "participant" | "judge" | "admin";

export type EventStatus = "draft" | "active" | "completed" | "cancelled" | "archived";

export type EventStage =
  | "registration"
  | "team_formation"
  | "submission"
  | "evaluation"
  | "results"
  | "completed";

export type RoundStatus = "upcoming" | "active" | "completed";

export type SubmissionStatus = "submitted" | "evaluated" | "pending" | "reviewed";

export type ReportType = "summary" | "detailed" | "scores" | "participants";

// ─── Core Models ─────────────────────────────────────────────────────────────

export interface User {
  id: string;
  firebase_uid: string;
  email: string;
  name: string;
  role: UserRole;
  organization?: string;
  is_active: boolean;
  event_id?: string | null;
  is_event_scoped?: boolean;
}

export interface Event {
  id: string;
  name: string;
  type: string;
  description: string;
  status: EventStatus;
  stage: EventStage;
  max_participants: number;
  hash: string;
  organizer_id: string;
  min_team_size?: number;
  max_team_size?: number;
  team_formation_type?: string;
  created_at?: string;
  updated_at?: string;
  participant_count?: number;
  team_count?: number;
  submission_count?: number;
  registration_opens_at?: string | null;
  registration_closes_at?: string | null;
  registration_form_fields?: RegistrationFormField[] | null;
  participants_model?: string | null;
  individual_registration_allowed?: boolean | null;
}

export interface Round {
  id: string;
  event_id: string;
  name: string;
  description?: string;
  status: RoundStatus;
  start_date?: string;
  end_date?: string;
  cutoff_score?: number | null; // single source of truth for advancement (#13)
  is_quiz?: boolean;
  live_judging?: boolean;
  anonymous?: boolean;
  scoring_mode?: string;
  created_at?: string;
}

export interface Participant {
  id: string;
  event_id: string;
  name: string;
  email: string;
  institution?: string;
  skills?: string[];
  gender?: string;
  age?: number;
  phone?: string;
  is_verified?: boolean;
  created_at?: string;
  /** Tailored registration-form answers (field_id → value), per the event's form. */
  registration_data?: Record<string, unknown> | null;
}

export interface TeamMember {
  id: string;
  team_id: string;
  participant_id: string;
  is_leader: boolean;
  joined_at?: string;
  participant?: Participant;
  user?: User;
}

export interface Team {
  id: string;
  event_id: string;
  name: string;
  theme_id?: string;
  members?: TeamMember[];
  created_at?: string;
}

export interface RubricCriterion {
  id: string;
  round_id: string;
  name: string;
  description?: string | null;
  max_score: number;
  position: number;
}

export interface JudgeAssignment {
  id: string;
  judge_id: string;
  event_id?: string;
  team_id?: string;
  round_id?: string;
  assigned_at?: string;
  judge?: User;
  event?: Event;
  round?: Round;
}

export interface Judge {
  id: string;
  event_id: string;
  name: string;
  email: string;
  institution?: string;
  expertise?: string[];
  role_label?: string; // Task 3: Reviewer / Investor / Jury / … ("Judge" default)
  rating?: number;
  is_verified?: boolean;
  created_at?: string;
}

export interface Submission {
  id: string;
  team_id: string;
  round_id: string;
  attachments: string[];
  status: SubmissionStatus;
  submitted_at?: string;
  team?: Team;
  round?: Round;
  score?: number;
  final_score?: number;
  panel_average?: number;
  evaluations?: Evaluation[];
}

export interface Evaluation {
  id: string;
  submission_id: string;
  judge_id: string;
  // Backend returns total_score. `score` is kept as a legacy fallback only.
  total_score?: number;
  score?: number;
  rubric_scores?: Record<string, number>;
  feedback?: string;
  evaluated_at?: string;
  judge?: User;
}

export interface Report {
  id: string;
  event_id: string;
  title: string;
  type: ReportType;
  data?: Record<string, unknown>;
  generated_at?: string;
  created_at?: string;
}

// ─── AI Types ─────────────────────────────────────────────────────────────────

export interface AIChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface BlueprintPreview {
  summary: string;
  confidence: number;
  questions: string[];
  suggestions?: string[];
  contradictions: string[];
  missing: string[];
  ready: boolean;
  blueprint: Record<string, unknown>;
}

export interface AIChatResponse {
  message: string;
  event_config: EventConfig | null;
  is_complete: boolean;
  event_id?: string;
  blueprint_preview?: BlueprintPreview | null;
}

export interface EventConfig {
  name?: string;
  type?: string;
  description?: string;
  max_participants?: number;
  team_size?: number;
  rounds?: Array<{
    name: string;
    duration?: string;
  }>;
  judging_criteria?: string[];
  prizes?: string[];
  [key: string]: unknown;
}

export interface AIDeployResponse {
  success: boolean;
  event_id?: string;
  hash?: string;
  file_path?: string;
}

// ─── Approvals ────────────────────────────────────────────────────────────────

export type ApprovalRequestType =
  | "team_formation"
  | "judge_assignment"
  | "email_batch"
  | "leaderboard_publish"
  | "stage_transition"
  | "progression"
  | "registration_form"
  | "event_deploy"
  | "anomaly_review";

export type ApprovalStatus =
  | "draft"
  | "pending"
  | "approved"
  | "rejected"
  | "revised";

export interface ApprovalRequest {
  id: string;
  event_id: string;
  request_type: ApprovalRequestType;
  status: ApprovalStatus;
  // Free-form proposal payload (shape depends on request_type).
  payload: Record<string, unknown>;
  requested_by?: string | null;
  reviewed_by?: string | null;
  review_notes?: string | null;
  requested_at: string;
  reviewed_at?: string | null;
}

export interface ApprovalActionBody {
  action: ApprovalStatus; // approve | reject | revise (matches enum)
  review_notes?: string;
  cutoff_score?: number; // for pipeline advancement approvals
}

// ─── Pipeline ─────────────────────────────────────────────────────────────────

export interface PipelineStep {
  id: string;
  label: string;
  round_id?: string;
  status?: "done" | "active" | "upcoming";
}

export interface PipelineState {
  steps: PipelineStep[];
  current_step: string | null;
  ready_to_advance: boolean;
  next_step: string | null;
  eliminated_team_ids: string[];
  closed_submission_round_ids?: string[];
}

// ─── Notifications ────────────────────────────────────────────────────────────

export type NotificationType = "info" | "alert" | "action_required";

export interface Notification {
  id: string;
  event_id: string;
  user_id: string;
  title: string;
  message: string;
  type: NotificationType;
  is_read: boolean;
  action_link?: string | null;
  created_at: string;
}

// ─── Anomalies ────────────────────────────────────────────────────────────────

export type AnomalyType = "score_variance" | "bias_detected" | "time_anomaly";

export interface Anomaly {
  id: string;
  event_id: string;
  evaluation_id: string;
  anomaly_type: AnomalyType;
  severity: number; // 0.0 - 1.0
  description: string;
  // Organizer-approval gate (#2): pending = awaiting organizer; approved =
  // considered (judge notified); rejected = dismissed.
  review_status?: "pending" | "approved" | "rejected";
  is_resolved: boolean;
  resolved_by?: string | null;
  resolved_at?: string | null;
  created_at: string;
}

// One rubric criterion within a judge's flagged evaluation, with their score.
export interface MyAnomalyRubricItem {
  id: string;
  name: string;
  max_score: number;
  description?: string | null;
  my_score: number;
}

// A judge's own anomaly, enriched for the private fix-it page.
export interface MyAnomaly {
  id: string;
  event_id: string;
  anomaly_type: AnomalyType;
  severity: number;
  description: string;
  is_resolved: boolean;
  created_at: string | null;
  submission_id: string;
  round_id: string;
  round_name: string;
  team_name: string | null;
  my_total_score: number | null;
  panel_average: number | null;
  rubric: MyAnomalyRubricItem[];
}

// ─── API Request Bodies ────────────────────────────────────────────────────────

export interface LoginBody {
  name?: string;
  role?: UserRole;
}

export interface CreateEventBody {
  name: string;
  type: string;
  description: string;
  status?: EventStatus;
  stage?: EventStage;
  max_participants: number;
  hash: string;
  // PR #7 made organizer_id required on the backend schema. We populate it
  // from the signed-in user's profile.id.
  organizer_id: string;
  min_team_size?: number;
  max_team_size?: number;
  team_formation_type: "platform_generated" | "preformed";
}

export interface UpdateEventBody {
  name?: string;
  type?: string;
  description?: string;
  status?: EventStatus;
  stage?: EventStage;
  max_participants?: number;
}

export interface CreateRoundBody {
  event_id: string;
  name: string;
  description?: string;
  status?: RoundStatus;
  start_date?: string;
  end_date?: string;
}

export interface RegisterParticipantBody {
  name: string;
  email: string;
  event_id: string;
  institution?: string;
  skills?: string[];
  gender?: string;
  age?: number;
  phone?: string;
}

export interface CreateTeamBody {
  event_id: string;
  name: string;
  theme_id?: string;
}

export interface AssignTeamMemberBody {
  team_id: string;
  participant_id: string;
  is_leader: boolean;
}

export interface UploadSubmissionBody {
  team_id: string;
  round_id: string;
  attachments: string[];
}

export interface SubmitEvaluationBody {
  submission_id: string;
  judge_id: string;
  // Backend EvaluationCreate requires `total_score` (0-100) and
  // `rubric_scores` (Dict[str, float]). The frontend currently uses a
  // single overall score so we surface that as both `total_score` and a
  // one-key rubric. When the rubric-schema endpoint exists, switch this
  // to a per-criterion form.
  total_score: number;
  rubric_scores: Record<string, number>;
  feedback?: string;
}

export interface AssignJudgeBody {
  judge_id: string;
  team_id?: string;
  event_id?: string;
  round_id?: string;
}

export interface InviteJudgeBody {
  email: string;
  event_id: string;
  name?: string;
  institution?: string;
  expertise?: string[];
}

export interface GenerateReportBody {
  event_id: string;
  title: string;
  type: ReportType;
  data?: Record<string, unknown>;
}

export interface AutoFormTeamsResponse {
  success: boolean;
  teams: Team[];
  leftovers: Participant[];
  message: string;
}

// ─── Themes ───────────────────────────────────────────────────────────────────

export interface Theme {
  id: string;
  event_id: string;
  name: string;
  description?: string;
  required_skills?: string[];
  created_at?: string;
}

// ─── Team Preferences ─────────────────────────────────────────────────────────

export interface TeamPreference {
  id: string;
  team_id: string;
  participant_id: string;
  preferred_name: string;
  preferred_theme_id: string | null;
  submitted_at: string;
}

// ─── Dashboard Response Shapes ────────────────────────────────────────────────

export interface ParticipantDashboard {
  team: { id: string; name: string; theme_id?: string | null; member_count?: number } | null;
  submissions: Array<{ id: string; round_id: string; final_score?: number | null; submitted_at?: string }>;
  progression_status: "pending" | "advancing" | "eliminated";
  evaluators?: Array<{ id: string; name: string; institution?: string | null; expertise?: string[] }>;
  notifications: Array<{ id: string; title: string; message: string; type: string; created_at: string }>;
}

export interface JudgeDashboard {
  assigned_teams: Array<{ team_id: string; team_name: string; theme_id?: string | null; submission_id?: string | null }>;
  pending_evaluations: Array<{ submission_id: string; team_name: string; team_id: string }>;
  completed_evaluations: Array<{ submission_id: string; team_name: string; score: number; evaluated_at: string }>;
  notifications: Array<{ id: string; title: string; message: string; type: string; created_at: string }>;
  summary: { total_assigned: number; pending: number; completed: number };
}

export interface OrganizerDashboard {
  stats: {
    total_participants: number;
    total_judges: number;
    total_teams: number;
    total_submissions: number;
    pending_approvals: number;
  };
  pending_approvals: Array<{ id: string; request_type: string; requested_by?: string | null; requested_at: string; status: string }>;
  anomalies: Array<{ id: string; anomaly_type: string; severity: number; description: string; created_at: string }>;
  rounds: Array<{ id: string; name: string; status: string; start_date?: string; end_date?: string }>;
}

export interface TeamFormationConstraint {
  type: "avoid_same_college" | "gender_diversity" | "balance_experience" | "required_skill";
  min_per_team?: number;
  skill?: string;
  min_count?: number;
}

export interface AssessmentGuideCriterion {
  criterion: string;
  max_score?: number;
  what_to_look_for: string;
  scoring_tips?: string;
}

export interface AssessmentGuide {
  challenge: string;
  overview: string;
  criteria_guides: AssessmentGuideCriterion[];
  key_questions: string[];
  generated_by?: "ai" | "rules";
}

// ─── Public registration page (Task 6) ───────────────────────────────────────

export interface RegistrationFormField {
  field_id: string;
  label: string;
  type: string; // text | email | tel | url | select | textarea | number | date
  required?: boolean;
  options?: string[];
  unique_per_event?: boolean;
}

export interface PublicEventCard {
  hash: string;
  name: string;
  type: string;
  description?: string | null;
  registration_open: boolean;
  registration_closes_at?: string | null;
  format: string; // "individual" | "team"
  team_registration: boolean;
}

export interface PublicRoundSummary {
  name: string;
  start_date?: string | null;
  end_date?: string | null;
}

export interface PublicEventDetail extends PublicEventCard {
  registration_form_fields: RegistrationFormField[];
  participants_model: string;
  individual_registration_allowed: boolean;
  min_team_size: number;
  max_team_size: number;
  rounds: PublicRoundSummary[];
}

export interface ResumeUploadResponse {
  url: string;
  name: string;
  prefill: Record<string, unknown>;
}

export interface PublicMemberRegistration {
  answers: Record<string, unknown>;
  resume_url: string;
  is_leader?: boolean;
}

export interface PublicRegisterRequest {
  captcha_token?: string;
  answers?: Record<string, unknown>;
  resume_url?: string;
  team_name?: string;
  members?: PublicMemberRegistration[];
}

// ─── API Response Wrappers ────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
  status?: number;
}
