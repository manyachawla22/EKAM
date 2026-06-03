# 🚀 EKAM — AI-Powered Event Orchestration Platform

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791)
![AI](https://img.shields.io/badge/AI-Groq%20LLM-purple)
![ML](https://img.shields.io/badge/ML-scikit--learn-orange)
![Optimization](https://img.shields.io/badge/Optimization-OR--Tools%20CP--SAT-red)
![Frontend](https://img.shields.io/badge/Frontend-Next.js-black)

---

## ✨ Overview

**EKAM** is an AI-powered event management and hackathon orchestration platform designed to automate and optimize the full lifecycle of competitions.

Instead of treating event management as a collection of forms and dashboards, EKAM approaches it as an **intelligent workflow problem**:

- Organizers describe events in **natural language**
- The platform converts that into a **structured event configuration**
- Teams and judges are assigned using **constraint-based optimization**
- Submissions and evaluations move through a **stage-aware pipeline**
- ML models validate scoring integrity and content similarity
- Reports, certificates, and notifications are generated automatically

The result is a platform that is not just operational, but **decision-supportive**.

---

## 🧠 Why EKAM is Different

Most event platforms stop at registration, dashboards, and basic CRUD workflows. EKAM goes further by integrating:

- **AI for event design and automation**
- **Optimization for team and judge assignment**
- **ML for validation and anomaly detection**
- **LLM-generated reports and certificates**
- **Stage-aware orchestration for real multi-round events**

This makes EKAM a strong example of **applied AI, backend systems, and optimization engineering** in one project.

---

## 🔥 Core Features

### 🤖 AI Event Creation
EKAM includes a chatbot that accepts natural language prompts from organizers and converts them into a structured event configuration.

It can extract and organize:
- event theme and type
- timeline and registration flow
- participant and team settings
- round structure
- judging setup
- prize information
- team formation constraints

The chatbot is designed with schema-guided extraction and backend-side validation so that the generated configuration remains aligned with the rest of the system.

---

### 🧑‍🤝‍🧑 Constraint-Based Team Formation
EKAM uses **Google OR-Tools CP-SAT** to form teams under real constraints such as:
- gender diversity
- institutional diversity
- skill distribution
- experience balancing

This moves team formation from a manual or random process to a formal optimization problem.

---

### 🧑‍⚖️ Constraint-Based Judge Assignment
Judges are assigned using optimization-aware logic based on:
- theme relevance
- expertise mapping
- workload balancing
- fairness constraints

This helps make the evaluation process more scalable and reliable.

---

### 🧪 ML-Based Anomaly Detection
EKAM uses **Isolation Forest** to detect abnormal judging patterns and suspicious scoring behavior such as:
- unusually lenient or harsh judges
- inconsistent scores
- outlier scoring patterns

These anomalies are surfaced to organizers through reports for review.

---

### 🕵️ Plagiarism Detection
The platform supports plagiarism and similarity detection across:
- PDFs
- local text/code files
- GitHub repositories

It extracts readable content and flags submissions whose similarity exceeds a defined threshold.

---

### 📊 Reports System
EKAM generates:
- event summary reports
- participant performance reports
- anomaly reports
- plagiarism reports

Participant performance reports are generated using an LLM call to provide personalized insights based on performance across rounds.

---

### 📜 Certificate Generation and Communication
EKAM supports:
- LLM-generated certificates
- fallback HTML certificate templates
- stage-wise email communication
- authentication and onboarding emails
- notifications for reports, progression, and outcomes

---

### 📂 CSV Uploads
The platform supports structured CSV onboarding for:
- participants
- judges

This makes large-scale event setup far easier for organizers.

---

### 🏗️ Full Event Lifecycle Management
EKAM supports:
- authentication and RBAC
- event orchestration
- approvals
- multi-round event progression
- submissions
- evaluations
- leaderboards
- communications
- organizer, judge, participant, and admin flows

---

## 🏗️ High-Level Architecture

```text
                         ┌─────────────────────────────┐
                         │         Frontend            │
                         │         Next.js             │
                         │ Organizer / Judge / User UI │
                         └──────────────┬──────────────┘
                                        │
                                        │ HTTP / JSON
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                               FastAPI Backend                              │
│                                                                            │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌──────────────────┐  │
│  │     AI Router       │   │   Core Routers      │   │   Report Router  │  │
│  │ /chat /deploy etc   │   │ events / teams /    │   │ anomalies /      │  │
│  │                     │   │ submissions / eval   │   │ plagiarism / LLM │  │
│  └─────────┬───────────┘   └──────────┬──────────┘   └─────────┬────────┘  │
│            │                          │                          │           │
│            ▼                          ▼                          ▼           │
│  ┌──────────────────┐      ┌────────────────────┐      ┌─────────────────┐  │
│  │  AI Config Layer │      │  Service Layer     │      │   ML / LLM      │  │
│  │ JSON draft/store │      │ modular business   │      │ anomaly, plag,  │  │
│  │ + schema cleanup │      │ logic              │      │ reports, certs  │  │
│  └─────────┬────────┘      └─────────┬──────────┘      └────────┬────────┘  │
│            │                         │                            │           │
│            ├──────────────┐          │                            │           │
│            ▼              ▼          ▼                            ▼           │
│      JSON Configs     PostgreSQL   OR-Tools CP-SAT         Groq / sklearn    │
│      (AI drafts)      (core data)  (team/judge assign)     (LLM / ML)        │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ System Design

### Backend Stack
- **FastAPI** for async API services
- **Async SQLAlchemy** for ORM and database access
- **PostgreSQL** for structured data storage
- **JSON config storage** for AI-generated draft and event configuration

### AI and ML Stack
- **Groq** for:
  - natural language event creation
  - participant performance reports
  - report/certificate content generation

- **scikit-learn** for:
  - Isolation Forest anomaly detection
  - TF-IDF based plagiarism and similarity detection

### Optimization Stack
- **Google OR-Tools CP-SAT** for:
  - team formation
  - judge assignment

### Frontend
- **Next.js** based frontend with organizer, judge, participant, and admin-facing flows

---

## 🧩 End-to-End Feature Set

EKAM includes end-to-end backend architecture and system integration for:

- Authentication
- RBAC
- Database design
- Event orchestration
- CSV upload
- Approvals
- Submissions
- Evaluations
- Leaderboards
- Communications
- Multi-round event management
- Dynamic event progression pipeline
- ML-based anomaly detection
- CP-SAT based team assignment
- CP-SAT based judge assignment
- AI-powered event creation chatbot
- Plagiarism detection
- LLM-generated participant reports
- Certificate generation and email delivery

---

## 🤖 How the AI Chatbot Works

The chatbot is designed to convert free-form organizer instructions into structured event definitions while staying compatible with the backend.

### Flow
1. Organizer describes the event in natural language
2. The AI layer extracts structured fields such as:
   - event type
   - rounds
   - constraints
   - judges
   - prizes
   - timeline
3. Backend validation and cleanup ensure the configuration remains usable
4. The config is stored as a draft/event JSON representation
5. Deployment finalizes the event into the EKAM workflow

### Why this matters
This makes event creation significantly faster and lowers the barrier for organizers, while still preserving backend structure and control.

### Example
A prompt like:

> Create a 3-round AI hackathon for 50 teams of 4, with gender-diverse teams, one screening round and one final demo round.

can be turned into a structured config containing:
- team size
- capacity
- rounds
- team-matching constraints
- event type and theme metadata

---

## 🧑‍🤝‍🧑 How Team Formation Works

Team formation is modeled as an optimization problem.

### Inputs
- participant data
- AI-derived or organizer-defined constraints
- team size bounds
- diversity requirements
- institution and skill preferences

### Solver
EKAM uses **Google OR-Tools CP-SAT** to solve the team assignment problem.

### Goals
- satisfy hard constraints
- maximize team quality and fairness
- avoid naive/manual grouping

### Example constraints
- avoid too many members from the same institute
- ensure skill coverage within a team
- balance experience levels
- include diversity-aware allocation

This is one of the strongest technical components of EKAM because it moves team formation from heuristics to formal optimization.

---

## 🧑‍⚖️ How Judge Assignment Works

Judge assignment follows a similar principle:
- judges are matched to submissions, teams, or rounds
- expertise and theme relevance are considered
- assignment load is balanced
- conflicts are reduced where possible

This makes the evaluation process more fair, scalable, and explainable.

---

## 🧪 ML Components

### 1. Anomaly Detection in Judging
EKAM uses **Isolation Forest** to identify suspicious scoring behavior such as:
- abnormally lenient or harsh judges
- inconsistent scoring patterns
- outlier score distributions

These anomalies are surfaced through reports for organizer review.

### 2. Plagiarism Detection
EKAM compares submission content across:
- PDFs
- code/text files
- GitHub repositories

The pipeline:
1. extracts readable content
2. vectorizes it using TF-IDF
3. computes similarity
4. flags suspiciously similar submissions

This helps preserve evaluation integrity in both coding and idea-based events.

---

## 📊 Reports System

The reports system includes:
- event summary reports
- participant performance reports
- anomaly reports
- plagiarism reports

### Participant Performance Reports
These are generated using an LLM call to produce personalized performance summaries for each participant or team based on their competition journey and outcomes.

### Event Reports
Organizers can generate richer event-level summaries for operational review and post-event analysis.

---

## 📜 Certificate Generation

EKAM can:
- generate certificates using LLM-generated HTML
- fall back to static HTML templates if needed
- send certificates via email automatically

This is integrated into the platform workflow rather than treated as a disconnected feature.

---

## 🖥️ Frontend Experience

The frontend includes:

### Public and Landing
- landing page
- login
- sign up

### Organizer Dashboard
- overview
- rounds
- participants and judges
- teams
- submissions
- leaderboard
- approvals
- anomalies
- reports

### Judge Dashboard
- assignments
- evaluation flows
- score submission

### Participant Dashboard
- team view
- event progress
- submissions
- results
- reports

### Admin Pages
- overview
- event control and monitoring

---

## 🔌 API Overview

This README does not dump every single endpoint, but the backend is organized cleanly by domain.

### AI
```text
POST /ai/chat
POST /ai/deploy
GET  /ai/events
GET  /ai/events/{hash}
GET  /ai/events/{event_id}/detail
```

### Authentication
```text
POST /auth/signup
POST /auth/login
POST /auth/otp
POST /auth/magic-link
```

### Events and Rounds
```text
POST /events/create
GET  /events/{event_id}
GET  /events
POST /rounds/create
GET  /rounds/{event_id}
```

### Participants and Judges
```text
GET  /participants/{event_id}
POST /participants/{event_id}
POST /events/{event_id}/participants/upload-csv

GET  /judges/{event_id}
POST /judges/{event_id}
POST /events/{event_id}/judges/upload-csv
```

### Teams
```text
POST /teams/{event_id}/auto-form
GET  /teams/{event_id}
POST /teams/create
```

### Submissions and Evaluations
```text
POST /submissions/...
GET  /submissions/...
POST /evaluations/...
GET  /evaluations/...
```

### Reports and ML
```text
POST /reports/detect-anomalies/{event_id}
POST /reports/detect-plagiarism/{event_id}
POST /reports/{event_id}/generate
GET  /reports/{event_id}
GET  /reports/participant/{event_id}/{participant_id}
```

### Pipeline, Leaderboard, Approvals
```text
GET  /leaderboard/{event_id}
POST /pipeline/...
GET  /approvals/{event_id}
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/reject
```

---

## 📁 Project Structure

```text
EKAM/
├── backend/
│   ├── app/
│   │   ├── core/              # config, auth context, security, utils
│   │   ├── middleware/        # RBAC/auth middleware
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── routers/           # FastAPI route modules
│   │   ├── services/          # business logic/services
│   │   ├── team_formation/    # CP-SAT optimization logic
│   │   └── main.py            # app entrypoint
│   ├── alembic/               # migrations
│   └── requirements.txt
├── frontend_new/              # Next.js frontend
└── README.md
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL
- Node.js
- Groq API key
- SMTP credentials for email features

### Backend Setup

#### 1. Clone the repository
```bash
git clone <your-repo-url>
cd EKAM
```

#### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate
```

On Windows:
```bash
venv\Scripts\activate
```

#### 3. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 4. Configure environment variables
Create a `.env` file inside the backend directory.

Example:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ekam
GROQ_API_KEY=your_groq_api_key

SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email_user
SMTP_PASSWORD=your_email_password
SENDER_EMAIL=your_email@example.com
SENDER_NAME=EKAM

FRONTEND_URL=http://localhost:3000
```

#### 5. Run migrations
```bash
alembic upgrade head
```

#### 6. Start the backend
```bash
uvicorn app.main:app --reload
```

Backend should now be available at:
```text
http://127.0.0.1:8000
```

#### 7. Open API docs
```text
http://127.0.0.1:8000/docs
```

---

## 🌐 Frontend Setup

```bash
cd frontend_new
npm install
npm run dev
```

Frontend should be available at:
```text
http://localhost:3000
```

---

## 🔐 Environment Variables

Typical environment variables used by EKAM include:

```env
DATABASE_URL=
GROQ_API_KEY=
SMTP_SERVER=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
SENDER_EMAIL=
SENDER_NAME=
FRONTEND_URL=
```

Depending on deployment, you may also configure:
- storage credentials
- JWT/auth secrets
- analytics keys
- deployment-specific service URLs

---

## 💪 Strengths of the Project

EKAM is strong in:
- full-stack system integration
- AI and backend orchestration
- optimization modeling
- ML-based evaluation integrity
- modular backend design
- multi-role product flow

This is not just a collection of APIs. It is a coordinated event management engine.

---

## 🔮 Future Improvements

- semantic plagiarism detection using embeddings
- richer explainability for anomaly detection
- real-time constraint tuning UI for organizers
- deeper analytics dashboards
- production-grade observability and logging
- background job queue for heavy tasks
- stronger file processing and storage abstraction

---

## 🎯 Who This Project Is For

EKAM is especially relevant for:
- hackathon organizers
- university event platforms
- coding competitions
- multi-round evaluations
- applied AI and systems engineering showcases

It also makes a strong portfolio project for:
- backend engineering roles
- applied ML roles
- AI systems internships
- research projects involving orchestration, optimization, or automation

---

## 🌟 Why This Project Is Portfolio-Strong

EKAM demonstrates more than one technical skill. It combines:

- backend architecture
- API design
- database modeling
- RBAC and auth
- optimization
- applied ML
- LLM integration
- workflow automation
- product thinking

That combination makes it a strong representation of **systems thinking**, not just implementation.

---

## Final Note

EKAM was built as an attempt to rethink event management as an **intelligent orchestration problem** rather than a simple dashboard problem.

The interesting part is not just that it has AI features.  
The interesting part is that **AI, ML, optimization, and backend workflows are all connected into one coherent system**.