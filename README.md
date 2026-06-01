# EKAM — Autonomous Event Operating System


## What is EKAM?

EKAM is an intelligent, LLM-powered event management platform that orchestrates the full operational lifecycle of any competitive event — hackathons, case competitions, debate tournaments, sports events — without manual coordination.

Most organizations manage events through spreadsheets, manual emails, and ad-hoc coordination. EKAM replaces this entirely with an autonomous pipeline where the committee defines the rules, participants and evaluators interact through purpose-built interfaces, and the system ensures nothing falls through the cracks.

## The Problem

Running a competitive event involves:
- Forming balanced teams from hundreds of applicants
- Sending contextually appropriate communications at every stage
- Coordinating judges, collecting scores, detecting anomalies
- Managing approvals before every irreversible action
- Generating reports for organizers and sponsors

Today this is all done manually. EKAM automates it end to end.

## Key Features

### Event Intelligence Layer
- Natural language event parser — describe your event in plain English, EKAM extracts structured configuration automatically using Gemini
- Intelligent validation — detects incomplete or contradictory descriptions and asks smart clarifying questions before proceeding
- Dynamic pipeline generation — configures event stages, scoring criteria, team rules, and communication touchpoints from a single description
- Supports any event format: hackathons, case competitions, debate tournaments, sports events

### Participant Management
- Registration portal with role-based access control (committee, participant, judge)
- CSV upload for bulk participant intake
- ATS-style resume scoring for applicant screening
- Real-time registration dashboard for committee

### Team Formation (CP-SAT Optimization)
- Encodes each participant as a feature vector across skills, domain, and experience level
- Computes cosine distance matrix to quantify inter-participant diversity
- Uses Google OR-Tools CP-SAT solver to find optimal team assignments:
  - Maximizes total pairwise diversity across all teams
  - Hard constraint: each participant assigned to exactly one team
  - Hard constraint: exact team size enforcement
  - Hard constraint: no two participants from same institution per team
- Gemini LLM generates human-readable rationale per team explaining the grouping logic
- Full committee approval gate before any assignments are communicated to participants

### Judge & Mentor Assignment
- Similarity-based matching — judge expertise matched to team domain (opposite objective to team formation)
- CP-SAT ensures balanced workload distribution across judges
- Conflict of interest detection based on institutional affiliation
- JWT magic links for judge portal access — no account creation required
- Scoped tokens — each judge can only view and score their assigned teams

### Evaluation Pipeline
- Gemini-generated scoring rubrics per team tailored to event criteria
- Independent score collection through judge portal
- Real-time score aggregation with configurable weighting per criterion
- Anomaly detection when judge scores diverge beyond configurable threshold
- LLM-powered divergence summary explaining why scores differ based on written feedback
- Committee approval gate before results are published

### Autonomous Communications
- LLM-drafted emails at every pipeline stage
- Welcome messages, team assignments, judge notifications, deadline reminders, progression invitations, results announcements
- Full communication log with delivery status per recipient
- Preview and approval before any email is sent

### Committee Dashboard
- Real-time event stage tracker with visual pipeline
- Pending approval items with approve/reject controls
- Live leaderboard with score breakdowns and anomaly indicators
- Full activity log of every system action
- Distribution rule configuration UI
- Judge and mentor management

### Participant Portal
- Read-only status page showing current stage, team details, evaluator info, key dates
- Progression invitation with confirmation for qualifying teams
- Personalized feedback delivery after results

### Post-Event Intelligence
- Auto-generated post-event report: participation stats, score distributions, judge bias analysis, top team highlights, recommendations
- Gemini rewrites raw judge scores into constructive personalized feedback per team
- Sponsor digest: clean summary email auto-generated for stakeholders
- Simulation mode: dry-run entire event lifecycle with generated data in under 60 seconds

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python |
| Database | PostgreSQL, Firebase |
| Migrations | Alembic |
| Optimization | Google OR-Tools (CP-SAT) |
| LLM | Gemini API (google-genai) |
| Frontend | React |
| Auth | JWT — role-based (committee, participant, judge) |
| ML/Vectors | NumPy, scikit-learn |
| Async Tasks | FastAPI BackgroundTasks |

## Architecture
Committee describes event in plain English
↓
NLP Parser (Gemini) → structured JSON event config
Validation agent asks clarifying questions if incomplete
↓
Event stored in DB — pipeline stages configured dynamically
↓
REGISTRATION OPENS
Participants register via frontend portal
Role-based access control via JWT middleware
Data stored in PostgreSQL via FastAPI routers
↓
REGISTRATION CLOSES
↓
TEAM FORMATION
Feature vectors built per participant (skills + domain + experience)
Cosine distance matrix computed
CP-SAT maximizes diversity, enforces hard constraints
Gemini generates rationale per team
↓
Committee Approval Gate #1 — approve or reject compositions
↓
JUDGE ASSIGNMENT
Judge expertise vectors matched to team domain vectors
CP-SAT balances workload, flags institutional conflicts
JWT magic links generated and emailed per judge
↓
JUDGING PHASE
Judges score via scoped portal
Gemini generates evaluation rubric per team
Scores collected independently per judge
↓
ANOMALY DETECTION
Score divergence flagged automatically
Gemini explains divergence from written feedback
Committee resolves before results move forward
↓
Committee Approval Gate #2 — approve final results
↓
RESULTS + POST EVENT
Participant portal updated with scores and feedback
Gemini rewrites judge notes into constructive paragraphs
Post-event report and sponsor digest auto-generated
Event archived for future reference

## Repository Structure
EKAM/
├── Frontend/                        # React — committee dashboard, participant
│                                    # portal, judge scoring interface
│
├── backend/
│   ├── alembic/                     # database migrations
│   ├── alembic.ini
│   ├── requirements.txt
│   └── app/
│       ├── main.py                  # FastAPI app entry point
│       ├── core/                    # database config, settings
│       ├── middleware/              # JWT auth, role-based access control
│       ├── models/                  # SQLAlchemy models
│       │                            # events, participants, teams, judges,
│       │                            # scores, communications
│       ├── schemas/                 # Pydantic request/response schemas
│       ├── routers/                 # FastAPI route handlers
│       │                            # auth, events, participants, teams,
│       │                            # judges, scores, communications
│       └── team_formation/          # CP-SAT optimization pipeline
│           ├── vectorizer.py        # participant → feature vector
│           ├── optimizer.py         # CP-SAT team assignment
│           ├── rationale.py         # Gemini rationale generation
│           ├── fake_participants.py # demo data (24 participants)
│           └── main.py              # pipeline orchestrator
│
└── README.md

## Team Formation — How It Works

Each participant is encoded as a 13-dimensional feature vector:
[ML, Backend, Frontend, Design, Cybersecurity, Research, Mobile, DevOps,  ← skills (8)
AI/ML, Web/App Dev, Cybersecurity, Cloud/DevOps,                          ← domain (4)
experience_normalized]                                                     ← experience (1)

CP-SAT solves:
Maximize: Σ dist(i,j) × pair(i,j,t)    for all pairs i,j in same team t
Subject to:
Σ x[i,t] = 1          ∀ participant i   (exactly one team)
Σ x[i,t] = team_size  ∀ team t          (exact team size)
Σ x[i,t] ≤ 1          ∀ institution     (no same institution per team)

## Running Locally

```bash
# clone
git clone https://github.com/khushiiii24/EKAM.git
cd EKAM

# backend setup
cd backend
pip install -r requirements.txt

# database migrations
alembic upgrade head

# environment variables
# Windows:
set GEMINI_API_KEY=your-key-here
# Mac/Linux:
export GEMINI_API_KEY=your-key-here

# run backend
uvicorn app.main:app --reload

# run team formation demo (fake data)
cd app/team_formation
python main.py
```

## Demo — Simulation Mode

EKAM includes a full simulation mode that runs the entire event lifecycle
using generated data in under 60 seconds — no real participants required.

```python
# in main.py — set use_fake=True
asyncio.run(run_team_formation(
    event_id="your-event-id",
    team_size=3,
    use_fake=True
))
```

Output: 8 fully formed teams with diversity scores and
Gemini-generated rationales printed to console.

## Human Approval Gates

EKAM enforces explicit committee sign-off before every irreversible action:

| Gate | Triggered Before |
|---|---|
| Gate 1 | Team assignments communicated to participants |
| Gate 2 | Results and scores published |
| Gate 3 | Progression invitations sent to qualifying teams |

No participant-facing action happens without committee approval.
=======

## What is EKAM?
EKAM is an intelligent, LLM-powered event management platform that orchestrates the full operational lifecycle of any competitive event — hackathons, case competitions, debate tournaments, sports events — without manual coordination.

Most organizations manage events through spreadsheets, manual emails, and ad-hoc coordination. EKAM replaces this entirely with an autonomous pipeline where the committee defines the rules, participants and evaluators interact through purpose-built interfaces, and the system ensures nothing falls through the cracks.

## The Problem

Running a competitive event involves:
- Forming balanced teams from hundreds of applicants
- Sending contextually appropriate communications at every stage
- Coordinating judges, collecting scores, detecting anomalies
- Managing approvals before every irreversible action
- Generating reports for organizers and sponsors

Today this is all done manually. EKAM automates it end to end.

## Key Features

### Event Intelligence
- Natural language event parser — describe your event in plain English, EKAM extracts structured configuration automatically
- Intelligent validation — detects incomplete or contradictory descriptions and asks smart clarifying questions
- Dynamic schema generation — creates database structure on the fly for any event format

### Team Formation (CP-SAT Optimization)
- Encodes each participant as a feature vector across skills, domain, and experience
- Computes cosine distance matrix to quantify participant diversity
- Uses Google OR-Tools CP-SAT to solve constrained optimization:
  - Maximizes total pairwise diversity across all teams
  - Hard constraint: each participant in exactly one team
  - Hard constraint: exact team size enforcement
  - Hard constraint: no two participants from same institution per team
- Gemini LLM generates human-readable rationale per team for committee review
- Full committee approval gate before any assignments are communicated

### Judge Assignment
- Similarity-based matching (opposite objective to team formation)
- Judge expertise vectors matched against team domain vectors
- CP-SAT ensures balanced workload distribution
- Conflict of interest detection (institution-based)
- JWT magic links for judge access — no account creation required

### Evaluation Pipeline
- Gemini-generated scoring rubrics per team based on event config
- Real-time score collection through judge portal
- Anomaly detection when judge scores diverge beyond configurable threshold
- LLM-powered divergence summary: explains *why* scores diverged based on written feedback
- Committee approval gate before results are published

### Communications
- Auto-drafted emails at every stage using Gemini
- Welcome messages, team assignments, judge notifications, deadline reminders, results
- Full communication log with delivery status
- Preview before sending — no irreversible action without committee sign-off

### Post-Event Intelligence
- Auto-generated post-event report: participation stats, score distributions, judge bias analysis, top team highlights
- Personalized feedback delivery: Gemini rewrites raw judge scores into constructive paragraphs per team
- Sponsor digest: clean summary email auto-generated for stakeholders
- Simulation mode: dry-run entire event lifecycle with generated data in under 60 seconds

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python |
| Database | PostgreSQL, Firebase |
| Optimization | Google OR-Tools (CP-SAT) |
| LLM | Gemini API (google-genai) |
| Frontend | React |
| Auth | JWT (role-based: committee, participant, judge) |
| ML/Vectors | NumPy, scikit-learn |
| Async Tasks | FastAPI BackgroundTasks |

## Architecture
Participant Registration
↓
Feature Vector Encoding (skills + domain + experience)
↓
CP-SAT Optimization (maximize diversity, respect constraints)
↓
Gemini Rationale Generation per team
↓
Committee Approval Gate
↓
Judge Assignment (similarity matching via CP-SAT)
↓
JWT Magic Links → Judge Scoring Portal
↓
Anomaly Detection + LLM Divergence Summary
↓
Committee Approval Gate
↓
Results Publication + Post-Event Report

## Repository Structure
EKAM/
├── frontend/                  # React dashboard and portals
├── backend/
│   ├── app/
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routes/            # FastAPI route handlers
│   │   ├── middleware/        # JWT auth middleware
│   │   ├── core/              # Database config
│   │   └── team_formation/    # CP-SAT optimization pipeline
│   │       ├── vectorizer.py         # Participant → feature vector
│   │       ├── optimizer.py          # CP-SAT team assignment
│   │       ├── rationale.py          # Gemini rationale generation
│   │       ├── fake_participants.py  # Demo data
│   │       └── main.py               # Pipeline orchestrator
│   └── requirements.txt
└── README.md




>>>>>>> feature/team-formation
