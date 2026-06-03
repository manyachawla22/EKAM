EKAM
� � � � � � �
Overview
EKAM is an AI-powered event orchestration platform built for hackathons, competitions, and multi-round evaluation pipelines. It combines LLM-driven event creation, constraint-based optimization, ML validation, and automated reporting and communication into one end-to-end system.
Instead of treating event management as a set of forms and dashboards, EKAM approaches it as an intelligent workflow problem:
Organizers describe an event in natural language
The platform converts that into a structured event configuration
Teams and judges are assigned using optimization
Submissions and evaluations flow through a stage-aware pipeline
ML models validate scoring integrity and content similarity
Reports, certificates, and notifications are generated automatically
The result is a platform that is not just operational, but decision-supportive.
Why EKAM is Different
Most event platforms stop at registration, dashboards, and CRUD. EKAM goes further by integrating:
AI for event design and automation
Optimization for team and judge assignment
ML for validation and anomaly detection
LLM-generated reports and certificates
Stage-aware orchestration for real multi-round events
This makes EKAM a strong example of applied AI, backend systems, and optimization engineering in one project.
Core Capabilities
1. AI Event Creation
EKAM includes a chatbot that accepts natural language prompts from organizers and converts them into a structured event configuration.
It can extract and organize:
event theme and type
timeline and registration flow
participant and team settings
round structure
judging setup
prize information
team formation constraints
The chatbot is designed with schema-guided extraction and backend-side validation so the generated configuration remains aligned with the platform workflow.
2. Constraint-Based Team Formation
EKAM uses Google OR-Tools CP-SAT to form teams under real constraints such as:
gender diversity
institutional diversity
skill distribution
experience balancing
This moves team formation from a manual or random process to an optimization problem.
3. Constraint-Based Judge Assignment
Judges are assigned using optimization-aware logic based on:
theme and domain relevance
skills and expertise
balanced workload
fairness constraints
4. ML-Based Scoring Validation
EKAM uses Isolation Forest to detect abnormal judging patterns and scoring anomalies. Suspicious evaluations can be flagged for organizer review, making the scoring process more trustworthy.
5. Plagiarism Detection
The submission pipeline supports similarity analysis across:
PDFs
local text and code files
GitHub repositories
It extracts readable content and flags submissions whose similarity exceeds a configured threshold.
6. LLM-Powered Reporting
The platform generates:
participant performance reports
event summary reports
anomaly reports
plagiarism reports
Participant reports can include personalized feedback and suggestions generated through Groq.
7. Automated Communications
EKAM supports:
stage-wise email communication
authentication emails
result and report notifications
certificate generation and delivery
8. Full Event Lifecycle Management
The platform supports:
multi-round events
submissions and evaluations
leaderboards
approvals
pipeline progression
organizer, judge, participant, and admin flows
High-Level Architecture
Plain text
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
System Design
Backend Stack
FastAPI for async API services
Async SQLAlchemy for ORM and database access
PostgreSQL for structured event, participant, judge, team, submission, evaluation, and report data
JSON config storage for AI-generated draft and event configuration
AI and ML Stack
Groq for natural language event creation, participant performance reports, and certificate or report content generation
scikit-learn for:
Isolation Forest anomaly detection
TF-IDF based plagiarism and similarity detection
Optimization Stack
Google OR-Tools CP-SAT for:
team formation
judge assignment
Frontend
Next.js based frontend with organizer, judge, participant, and admin-facing flows
Feature Breakdown
Authentication and RBAC
EKAM includes:
signup and login flows
role-aware access
organizer, judge, participant, and admin boundaries
protected actions through backend authorization middleware
Event Orchestration
An organizer can define and manage:
multi-round events
submission phases
evaluation phases
approval checkpoints
dynamic event progression
CSV Uploads
The system supports structured CSV ingestion for:
participants
judges
This is useful for large events and bulk onboarding.
Approvals
EKAM includes approval-aware workflows for actions that should not be auto-executed blindly, improving traceability and organizer control.
Submissions and Evaluations
Participants can submit work and judges can evaluate through a pipeline that supports:
multi-round progression
scoring criteria
review flows
anomaly detection
Leaderboards
Leaderboards are generated dynamically based on evaluation outcomes and event progress.
Communications
The platform supports automated event-stage communication and report or certificate delivery.
How the AI Chatbot Works
The chatbot is designed to convert free-form organizer instructions into structured event definitions while staying compatible with the backend.
Flow
Organizer describes the event in natural language
The AI layer extracts structured fields such as:
event type
rounds
constraints
judges and prizes when provided
Backend validation and cleanup ensure the config remains usable
The config is stored as a draft or event JSON representation
Deployment finalizes the event into the EKAM workflow
Why this matters
This makes event creation significantly faster and lowers the barrier for organizers, while still preserving backend structure and validation.
Example
A prompt like:
Create a 3-round AI hackathon for 50 teams of 4, with gender-diverse teams, one screening round and one final demo round.
can be turned into a structured config containing:
team size
capacity
rounds
team-matching constraints
event type and theme metadata
How Team Formation Works
Team formation is modeled as an optimization problem.
Inputs
participant data
optional AI-derived constraints
team size bounds
diversity requirements
institution and skill preferences
Solver
EKAM uses Google OR-Tools CP-SAT to solve the assignment problem.
Goals
satisfy hard constraints
maximize team quality and fairness
avoid naive or manual grouping
Example constraints
avoid too many members from the same institute
include required skills per team
improve balance across teams
This is one of the strongest technical parts of EKAM because it moves team assignment from heuristics to formal optimization.
How Judge Assignment Works
Judge assignment follows a similar principle:
judges are matched to submissions, teams, or rounds
expertise and theme relevance are considered
assignment load is balanced
conflicts are avoided where possible
This makes the evaluation process more fair and scalable.
ML Components
1. Anomaly Detection in Judging
EKAM uses Isolation Forest to identify suspicious scoring behavior such as:
abnormally lenient or harsh judges
highly inconsistent scoring patterns
outlier score distributions
These anomalies are surfaced to organizers through reports.
2. Plagiarism Detection
EKAM compares submission content across:
PDFs
code and text files
GitHub repositories
The pipeline:
extracts readable content
vectorizes it using TF-IDF
computes similarity
flags suspiciously similar submissions
This helps preserve evaluation integrity in coding and idea-based events.
Reports System
The reports system includes:
event summary reports
participant performance reports
anomaly reports
plagiarism reports
Participant Performance Reports
These are generated using an LLM call to produce personalized performance summaries for each participant or team based on their competition journey and outcomes.
Event Reports
Organizers can generate richer reports for operational review and post-event analysis.
Certificate Generation
EKAM can:
generate certificates using LLM-generated HTML
fall back to static HTML templates if needed
send certificates through email automatically
This is integrated into the event progression flow rather than treated as a disconnected feature.
Frontend Experience
The frontend includes:
Public and Landing
landing page
login and sign up
Organizer Dashboard
overview
rounds
participants and judges
teams
submissions
leaderboard
approvals
anomalies
reports
Judge Dashboard
assignments
evaluation flows
score submission
Participant Dashboard
team view
event progress
submissions
results and reports
Admin Pages
overview
event control and monitoring
API Overview
This README does not list every route individually, but the backend is organized by domain.
AI
Plain text
POST /ai/chat
POST /ai/deploy
GET  /ai/events
GET  /ai/events/{hash}
GET  /ai/events/{event_id}/detail
Authentication
Plain text
POST /auth/signup
POST /auth/login
POST /auth/otp
POST /auth/magic-link
Events and Rounds
Plain text
POST /events/create
GET  /events/{event_id}
GET  /events
POST /rounds/create
GET  /rounds/{event_id}
Participants and Judges
Plain text
GET  /participants/{event_id}
POST /participants/{event_id}
POST /events/{event_id}/participants/upload-csv

GET  /judges/{event_id}
POST /judges/{event_id}
POST /events/{event_id}/judges/upload-csv
Teams
Plain text
POST /teams/{event_id}/auto-form
GET  /teams/{event_id}
POST /teams/create
Submissions and Evaluations
Plain text
POST /submissions/...
GET  /submissions/...
POST /evaluations/...
GET  /evaluations/...
Reports and ML
Plain text
POST /reports/detect-anomalies/{event_id}
POST /reports/detect-plagiarism/{event_id}
POST /reports/{event_id}/generate
GET  /reports/{event_id}
GET  /reports/participant/{event_id}/{participant_id}
Pipeline, Leaderboard, Approvals
Plain text
GET  /leaderboard/{event_id}
POST /pipeline/...
GET  /approvals/{event_id}
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/reject
Project Structure
Plain text
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
Local Setup
Prerequisites
Python 3.10+
PostgreSQL
Node.js
Groq API key
SMTP credentials for email features
Backend Setup
1. Clone the repository
Bash
git clone <your-repo-url>
cd EKAM
2. Create a virtual environment
Bash
python -m venv venv
source venv/bin/activate
On Windows:
Bash
venv\Scripts\activate
3. Install backend dependencies
Bash
cd backend
pip install -r requirements.txt
4. Configure environment variables
Create a .env file inside the backend directory.
Example:
Environment
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ekam
GROQ_API_KEY=your_groq_api_key

SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email_user
SMTP_PASSWORD=your_email_password
SENDER_EMAIL=your_email@example.com
SENDER_NAME=EKAM

FRONTEND_URL=http://localhost:3000
5. Run migrations
Bash
alembic upgrade head
6. Start the backend
Bash
uvicorn app.main:app --reload
Backend should now be available at:
Plain text
http://127.0.0.1:8000
7. Open API docs
Plain text
http://127.0.0.1:8000/docs
Frontend Setup
Bash
cd frontend_new
npm install
npm run dev
Frontend should be available at:
Plain text
http://localhost:3000
Environment Variables
Typical environment variables used by EKAM include:
Environment
DATABASE_URL=
GROQ_API_KEY=
SMTP_SERVER=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
SENDER_EMAIL=
SENDER_NAME=
FRONTEND_URL=
Depending on deployment, you may also configure:
storage credentials
JWT or auth secrets
analytics keys
deployment-specific service URLs
Current Strengths
EKAM is already strong in:
full-stack system integration
AI and backend orchestration
optimization modeling
ML-based evaluation integrity
modular backend design
multi-role product flow
This is not just a collection of APIs. It is a coordinated event management engine.
Future Improvements
semantic plagiarism detection using embeddings
richer explainability for anomaly detection
real-time constraint tuning UI for organizers
deeper analytics dashboards
production-grade observability and logging
background job queue for heavy tasks
stronger file processing and storage abstraction
Who This Project Is For
EKAM is especially relevant for:
hackathon organizers
university event platforms
coding competitions
multi-round evaluations
applied AI and systems engineering showcases
It also makes a strong portfolio project for:
backend engineering roles
applied ML roles
AI systems internships
research projects involving orchestration, optimization, or automation
Why This Project Is Portfolio-Strong
EKAM demonstrates more than one technical skill. It combines:
backend architecture
API design
database modeling
RBAC and auth
optimization
applied ML
LLM integration
workflow automation
product thinking
That combination makes it a strong representation of systems thinking, not just implementation.
Final Note
EKAM was built as an attempt to rethink event management as an intelligent orchestration problem rather than a simple dashboard problem.
The interesting part is not just that it has AI features.
The interesting part is that AI, ML, optimization, and backend workflows are all connected into one coherent system.



