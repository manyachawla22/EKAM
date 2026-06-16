# 🚀 EKAM — AI Event Operating System

 https://ekam-kohl.vercel.app/

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791)
![AI](https://img.shields.io/badge/AI-Gemini%20%2B%20Groq-purple)
![ML](https://img.shields.io/badge/ML-scikit--learn-orange)
![Optimization](https://img.shields.io/badge/Optimization-OR--Tools%20CP--SAT-red)
![Frontend](https://img.shields.io/badge/Frontend-Next.js%2015%20%2F%20React%2019-black)

---

## ✨ Overview

**EKAM** is an **AI-driven event operating system**. An organizer *describes* a
competition in plain English; EKAM turns that into a structured **Universal Blueprint**,
asks for what's missing, and — after the organizer approves — **builds and runs the
whole event end-to-end**.

The key idea: EKAM is **format-agnostic**. The same engine runs a hackathon, an
ideathon, a case competition, a coding contest / CTF, a quiz, a knockout tournament
(esports / chess / sports), or a research symposium — because the AI maps every event
onto a small set of building blocks ("primitives") instead of needing custom code per
format. Unknown formats (debate, MUN, scholarship…) are mapped onto the same primitives
and still run end-to-end.

### The mental model (three rules that explain everything)

1. **The AI proposes. Python guarantees. The human approves.** Nothing irreversible
   (deploy, team formation, judge panels, emails, winners, anomaly reveal) happens
   without an organizer clicking approve.
2. **The blueprint is the source of truth.** Which stages exist and which per-round
   flags are on (auto-scoring / anonymous / live / quiz) all come from the approved
   blueprint stored on the event.
3. **The pipeline is a loop.** Figure out the current step → check its real-world
   condition → propose an approval → on approval, run the effect and advance. Same loop
   for every format.

---

## 🧠 Why EKAM is different

Most event platforms stop at registration, dashboards, and CRUD. EKAM is an
**orchestration engine**:

- **AI for event *design*** — not just form-filling, but inferring the full pipeline
  (stages, roles, scoring, progression) from a description, with a deterministic safety
  net so a sloppy or absent LLM still yields a runnable event.
- **Optimization (CP-SAT)** for team formation and judge assignment.
- **ML** for scoring-anomaly detection and plagiarism/similarity.
- **A resilient LLM layer** — Gemini (key-pool rotation) with automatic Groq fallback.
- **Human-in-the-loop approvals** on everything irreversible.

---

## 🔥 Core Features

### 🤖 AI Event Creation (Event OS)
- **Describe → blueprint → review → deploy.** A chat agent extracts the event onto the
  Universal Blueprint, asks only for what's genuinely required, and shows a live,
  editable preview.
- **Understands intent, not keywords** — "written aptitude test" → quiz; "1v1 knockout"
  → bracket; "double-blind" → anonymous review; "pitch live" → a live-judged round.
- **Always asks for evaluators** (judges / referees / reviewers) and event-specific data
  (a quiz's question bank, a tournament's match links).
- **Robust by construction** — deterministic normalization + validation fill ids,
  defaults, and clamps, so the event is runnable even if the model is imperfect.

### 🧩 7 built-in event types (+ anything else)
Hackathon · Ideathon · Case competition · Coding contest / CTF · Quiz / written test ·
Tournament / knockout · Symposium / paper review. Each has a canonical flow and tailored
registration fields; unknown formats are decomposed onto the same primitives.

### 🏆 Tournament brackets
Single-elimination knockouts: generate the tree (eliminated teams excluded, byes
rendered), referees score matches and winners auto-advance up the tree (live via SSE),
match links bulk-uploaded via CSV. Works for team *and* individual events.

### 📝 Quiz / question-bank engine
Upload a `.md`/`.csv` question bank; the platform generates a different paper per team;
participants upload one answer file; judges grade per-question **or** the AI auto-checks
against the answer key.

### 🧑‍🤝‍🧑 Constraint-based team formation (CP-SAT)
Form balanced teams from individual sign-ups (skills, diversity, size). Supports
**preformed** teams (a leader registers the whole team) and **platform-formed** teams.

### 🧑‍⚖️ Constraint-based judge assignment (CP-SAT)
Assign judges to teams/rounds with adaptive panel sizes; idempotent and re-approval safe.

### 🧪 Integrity: anomalies + plagiarism
Isolation-Forest scoring-anomaly detection (variance / bias / timing), organizer-gated
before the judge ever sees it; TF-IDF plagiarism/similarity across PDFs, code, and repos.

### 🌐 Public registration page
A shareable public sign-up page at `/register/<hash>` with a **per-format dynamic form**
(fields auto-chosen for the event — e.g. esports → in-game name, symposium → paper
title), Cloudflare-Turnstile bot protection, and hard gates on the registration window,
capacity, and per-event email uniqueness. Team events collect each member's details on
one form (first two required, the rest optional up to the max).

### 📄 Resume parsing & ATS
Participants can upload a resume PDF; EKAM extracts the text and uses the LLM seam (with
a regex name backstop for when the model is rate-limited) to pull structured details and
compute an **ATS-style score** used in skill-aware team formation.

### 📡 Real-time updates (Server-Sent Events)
A long-lived `GET /stream` SSE connection pushes "something changed" signals
(notifications, approvals, anomalies, pipeline/bracket changes) to the authenticated
user, so dashboards refresh instantly instead of waiting for a poll. Bracket match
scores propagate live this way. (The frontend uses a shared-SSE singleton; the backend
deliberately avoids pinning a DB connection to each open stream.)

### 📊 Reports, certificates & comms
Event/participant/anomaly/plagiarism reports (LLM-personalized where useful),
LLM-generated certificates, and approval-gated email + in-app notifications at every
touchpoint.

### 🔄 Dynamic, approval-gated pipeline
A per-event pipeline derived from the blueprint walks the event through registration →
formation → judge assignment → rounds (submission/evaluation/advancement, or a bracket)
→ winners — pausing at each irreversible step for organizer approval.

---

## 🏗️ Architecture

```text
                    Browser: Organizer · Participant · Judge
                                     │  HTTPS / SSE
                                     ▼
        ┌─────────────────────────────────────────────────────────┐
        │  FRONTEND — Next.js 15 / React 19 / TypeScript / Tailwind │
        │  organizer/* · participant/* · judge/* · /register/<hash> │
        └───────────────────────────┬─────────────────────────────┘
                                     │ REST + SSE
                                     ▼
        ┌─────────────────────────────────────────────────────────┐
        │  BACKEND — FastAPI (async)                                │
        │  routers/ → services/ → models/ (SQLAlchemy)              │
        │  Event OS (blueprint · validator · generator · pipeline)  │
        │  llm_client seam · CP-SAT · ML · approvals · event_bus    │
        └───────┬───────────────────┬───────────────────┬──────────┘
                ▼                   ▼                   ▼
        Gemini 2.5 (key pool)   PostgreSQL          Resend (email)
          → Groq fallback     (JSONB blueprints)   Firebase (org auth)
                                                   Local/ngrok file store
```

A full set of ASCII diagrams (ER, DFDs, user flows, orchestration loop, deploy
sequence) lives in [`.vscode/study/current_diagrams.md`](.vscode/study/current_diagrams.md).

---

## ⚙️ Tech Stack

**Backend** — FastAPI · async SQLAlchemy · PostgreSQL · Alembic (migrations) ·
Pydantic v2.
**AI** — Gemini 2.5 Flash (primary) with a multi-key pool, automatic **Groq** fallback,
optional Anthropic — all behind one `llm_client` seam.
**Optimization** — Google OR-Tools **CP-SAT** (team formation, judge assignment).
**ML** — scikit-learn (Isolation Forest anomalies; TF-IDF plagiarism).
**Email** — Resend. **Auth** — Firebase (organizers) + JWT/OTP/magic-link
(participants & judges). **Files** — local storage, served via ngrok for remote judges.
**Frontend** — Next.js 15, React 19, TypeScript, Tailwind v4, Firebase, framer-motion,
recharts, sonner. Live updates via **SSE**.

---

## 📁 Project Structure

```text
EKAM/
├── backend/
│   ├── app/
│   │   ├── core/         # config, database, auth context
│   │   ├── middleware/   # auth / RBAC
│   │   ├── models/       # SQLAlchemy tables (events, rounds, teams, submissions,
│   │   │                 #   judges, matches, quiz, approvals, pipeline, …)
│   │   ├── schemas/      # Pydantic request/response shapes
│   │   ├── routers/      # FastAPI endpoints (one per domain + ai, matches, quiz, stream)
│   │   ├── services/     # logic: Event OS (blueprint/validator/generator/pipeline),
│   │   │                 #   llm_client, CP-SAT, scoring, bracket, quiz, ML, comms…
│   │   └── main.py       # app entrypoint (+ a 60s deadline-sweep scheduler)
│   ├── alembic/          # migrations
│   ├── scripts/
│   │   └── eval_blueprints.py   # AI regression harness (10 event descriptions)
│   └── requirements.txt
├── frontend_new/         # Next.js app (THE active frontend)
├── .vscode/study/        # study docs: current_database / backend_map / ai_system /
│                         #   features / challenges_learnings / diagrams
├── expectation.md        # full behavior runbook (states + edge cases)
├── ai_expect.md          # per-event-type end-to-end expectations
└── README.md
```

> **Note:** the active frontend is **`frontend_new/`**.

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL
- Node.js 18+
- A **Gemini** API key (free tier works) — and/or a **Groq** key (fallback)
- A **Resend** API key (for email)
- A **Firebase** service-account JSON (organizer auth)

### Backend

```bash
git clone <your-repo-url>
cd EKAM

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

cd backend
pip install -r requirements.txt
```

Create `backend/.env` (see the full template below), then:

```bash
alembic upgrade head          # apply migrations
uvicorn app.main:app --reload # start the API
```

- API: `http://127.0.0.1:8000`
- Docs (Swagger): `http://127.0.0.1:8000/docs` (routes are under the `API_V1_STR` prefix)

### Frontend

```bash
cd frontend_new
npm install
npm run dev          # http://localhost:3000
```

---

## 🔐 Environment Variables (`backend/.env`)

EKAM loads settings via `pydantic-settings`, so the variables **without defaults are
required** — the app won't start if they're missing.

```env
# ----- App -----
PROJECT_NAME=EKAM
VERSION=1.0.0
API_V1_STR=/api/v1
DEBUG=true

# ----- Database (PostgreSQL) -----
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ekam
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ekam

# ----- Auth -----
FIREBASE_CREDENTIALS_PATH=./firebase-service-account.json
MOCK_AUTH=false
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ----- AI / LLM seam -----
# Primary provider for the Event-OS agent. "gemini" (default) | "groq" | "anthropic".
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_key
# OPTIONAL key pool to beat the free-tier 20 req/day limit. Comma-separated, and the
# keys MUST come from SEPARATE Google Cloud projects (same-project keys share a quota).
GEMINI_API_KEYS=key1,key2,key3
# Groq is the automatic fallback (and powers resume parsing etc.). Keep the model current.
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
ANTHROPIC_API_KEY=

# ----- Email (Resend) -----
# NOTE: email is sent via Resend; the Resend API key is read from SMTP_PASSWORD.
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=your_resend_api_key
EMAIL_FROM=EKAM <no-reply@yourdomain.com>

# ----- Frontend / links -----
FRONTEND_URL=http://localhost:3000
# Public base for uploaded-file links (set to your ngrok URL so remote judges can open
# PDFs). Empty ⇒ falls back to the request host.
PUBLIC_BASE_URL=
UPLOAD_DIR=uploads

# ----- Captcha (Cloudflare Turnstile, public registration) -----
# Empty ⇒ captcha verification is DISABLED (fine for dev/demo). Set in prod.
TURNSTILE_SECRET_KEY=
```

---

## 🔌 API Overview

All routes are served under the `API_V1_STR` prefix (e.g. `/api/v1`). Each router owns
its own sub-prefix. Highlights:

```text
# AI / Event OS (no internal prefix → /ai/*)
POST   /ai/chat                      # design/iterate the event in chat
GET    /ai/events, /ai/events/{hash} # AI-created events

# Core
GET/POST  /events, /events/{id}      # events; GET /events/{id}/features (flags)
GET/POST  /rounds                    # rounds (+ scoring/anonymous/live/quiz flags)
GET/POST  /participants, /teams, /judges
POST      /teams/{id}/upload-csv     # team roster import (+ sample-csv)
GET/POST  /submissions, /evaluations
GET/POST  /rubrics, /themes

# Event OS features
GET/POST  /matches/...               # bracket: generate, get, PATCH (score→advance), CSV links
GET/POST  /quiz/...                  # bank upload/paste, generate papers, my-paper,
                                     #   team paper (+answers), AI auto-grade

# Orchestration & comms
GET       /pipeline/...              # dynamic pipeline state + advance
GET/POST  /approvals/...             # the human-in-the-loop gate (approve/reject/revise)
GET/POST  /emails/..., /notifications/...
GET       /leaderboard/{event_id}
GET/POST  /anomalies/..., /reports/...
GET       /dashboard/...             # per-role dashboards
GET       /stream/...                # Server-Sent Events (live bracket/pipeline)

# Public (unauthenticated)
GET/POST  /public/register/{hash}    # the public registration page
```

Auth: organizers use **Firebase** (no `/auth/signup` password flow); participants and
judges use **OTP / magic-link** per event.

---

## 📚 Documentation

In-repo deep dives (kept current):

- **`expectation.md`** — full behavior runbook: states, what advances them, every edge
  case, and failure/recovery.
- **`ai_expect.md`** — what to expect per event type, end-to-end.
- **`.vscode/study/current_database.md`** — every table explained.
- **`.vscode/study/current_backend_map.md`** — all routers / services / schemas.
- **`.vscode/study/current_ai_system.md`** — the complete AI pipeline.
- **`.vscode/study/current_features.md`** — full feature list by role.
- **`.vscode/study/current_challenges_learnings.md`** — what was hard and what we learned.
- **`.vscode/study/current_diagrams.md`** — ASCII diagrams (ER, DFDs, flows, orchestration).

---

## 🧪 Dev: AI regression harness

Prompt edits to the AI agent can silently break extraction, so there's a harness:

```bash
cd backend
python scripts/eval_blueprints.py
```

It feeds 10 event descriptions (the 7 known types + unknowns like debate/MUN/scholarship,
using synonyms) through the extractor and prints each resulting blueprint + validation
verdict + derived flags (quiz / bracket / anonymous / auto / live). It runs without a DB
and degrades gracefully without an LLM key. (It also catches infra issues — e.g. a
decommissioned fallback model emptying results when Gemini is busy.)

---

## ⚠️ Good to know (operational notes)

- **Gemini free tier = 20 requests/day per key.** Use `GEMINI_API_KEYS` (separate
  projects) to multiply it, or a paid key. On a 429/503 the client rotates keys, then
  falls back to Groq.
- **Keep LLM model ids current.** A decommissioned model in the fallback chain silently
  empties results — the AI looks "dumb" but it's an infra issue.
- **Clock skew breaks Firebase auth** — a 401 "Token used too early" means the server
  clock drifted; sync it.
- **A background scheduler** sweeps every 60s to disqualify non-submitters past a
  deadline (idempotent, best-effort).
- **Remote judges:** set `PUBLIC_BASE_URL` to your ngrok URL so uploaded PDFs open.

---

## 🔮 Future Improvements

- Paid/tier-1 LLM to remove the free-tier daily ceiling.
- Sectioned extraction (separate small calls) if single-call extraction quality regresses.
- Richer quiz auto-grading (open-ended, partial credit).
- Semantic (embedding-based) plagiarism detection.
- Deeper analytics dashboards and production observability.
- Background job queue for heavy tasks.

---

## Final Note

EKAM rethinks event management as an **intelligent orchestration problem**. The
interesting part isn't that it has AI features — it's that **AI (extraction), Python
(guarantees), optimization (CP-SAT), ML (integrity), and human approvals** are wired
into one coherent engine that runs *any* event format from a plain-English description.
