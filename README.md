# EKAM — Autonomous Event Operating System

> "Describe any event in plain English. EKAM builds the workflow, handles registrations, forms teams, coordinates judging, detects anomalies, and publishes results — all autonomously."

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




