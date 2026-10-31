# VeriOps (CampusOps AI)

> **Investigate with evidence. Recover with confidence.**  
> Autonomous Incident Investigation & Recovery Agent for TCS Hackathon Challenge 01.

---

## 🌟 Overview

**VeriOps** is an autonomous, evidence-driven incident investigation and recovery platform designed for enterprise campus and cloud IT environments. When production incidents occur (such as HTTP 504 Gateway Timeouts, latency degradation, or service cascading failures), VeriOps performs:

1. **Network-First Diagnostic Triaging:** Evaluates physical core switches, border gateways, access points, and DNS resolvers before inspecting software layers to prevent unnecessary application restarts.
2. **Deterministic Evidence Correlation:** Correlates multi-source telemetry spanning application logs, infrastructure metrics, distributed traces, alerts, CI/CD deployment commits, configuration changes, and support tickets.
3. **Competing Hypothesis Generation:** Formulates and ranks multiple hypotheses with confidence scoring and evidence-backed rationales.
4. **Mandatory Human-in-the-Loop Authorization:** Enforces strict operator approval gates with required authorization notes before any remediation runbook can execute.
5. **Post-Recovery SLA Verification:** Autonomously validates 4 core SLA criteria (P99 Latency, Error Rate, Database Pool Capacity, Peak Throughput) to ensure system health.
6. **Dynamic Replanning on Failure:** Automatically transitions into a replanning loop if synthetic failure or regression is detected during verification.
7. **Cryptographic Evidence Export:** Produces verifiable, tamper-evident evidence bundle manifests with SHA-256 integrity checksums.
8. **Persistent 13-Stage Investigation Tracker:** Maintains an immutable audit trail mapping diagnostic tool calls, hardware device impacts, and milestone execution timestamps.

---

## 🏗️ Architecture & Technology Stack

```
CAMPUSOPS-AI/
├── frontend/                     # Next.js 16 (App Router) + TypeScript + Tailwind CSS
│   ├── src/app/                  # App Router pages (/incidents, /chat, /login, /register)
│   ├── src/components/           # Enterprise operations UI components
│   │   ├── dashboard/            # Executive SRE Overview & live telemetry charts
│   │   └── incidents/            # Lifecycle diagram, Service graph, Timeline, Tracker, Modals
│   └── src/types/                # TypeScript interfaces (Incident, Investigation, Auth)
├── backend/                      # Python 3.13 + FastAPI + SQLAlchemy Async
│   ├── app/
│   │   ├── routes/               # API routers (incidents, auth, chat, knowledge, health)
│   │   ├── services/             # Orchestrator, Diagnostic tools, Gemini RAG, Auth
│   │   ├── models/               # PostgreSQL / pgvector ORM models
│   │   └── schemas/              # Pydantic schemas
│   ├── alembic/                  # Database migration scripts
│   └── tests/                    # Pytest test suite (14 passing tests)
├── docker-compose.yml            # PostgreSQL 15.4 with pgvector container
└── docs/                         # Architecture and design documentation
```

### Core Technologies
- **Frontend:** Next.js 16.4.3 (Turbopack, App Router), TypeScript, Tailwind CSS, Lucide Icons
- **Backend:** FastAPI, Python 3.11+, SQLAlchemy 2.0 (Asyncpg), Pydantic v2
- **Database:** PostgreSQL 15.4 with `pgvector` extension
- **Security & Auth:** Argon2id password hashing, Google Identity Services OAuth, JWT session cookies
- **AI & RAG:** Google Gemini API, pgvector vector search, Cosine distance embeddings
- **Testing:** Pytest (Asyncio), ESLint, Next.js Production Build Validation

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- **Node.js:** ≥ 20.x
- **Python:** ≥ 3.11
- **Docker:** for PostgreSQL + pgvector container
- **Git**

### 2. Database Infrastructure
Start the dedicated database container:
```bash
docker compose up -d
```
*Database runs on `localhost:5434` (`campusops_db`).*

### 3. Backend Setup
```bash
cd backend

# Create & activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 4. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
- Web Application: `http://localhost:3000`
- Incidents Control Center: `http://localhost:3000/incidents`
- AI Knowledge Chat: `http://localhost:3000/chat`

---

## 🧪 Quality Gate & Test Suite

### Backend Test Suite (14 Tests)
```bash
cd backend
pytest -v tests/test_investigation.py tests/test_incidents.py
```
- ✅ `test_investigation_lifecycle_network_first_to_resolution`
- ✅ `test_investigation_failed_verification_triggers_replanning`
- ✅ `test_investigation_tracker_stages_and_device_mapping`
- ✅ `test_tracker_reflects_diagnostic_and_recovery_progression`
- ✅ `test_seed_demo_incident` & idempotency
- ✅ `test_incident_timeline_ordering_and_timestamps`
- ✅ `test_service_dependency_graph`
- ✅ `test_evidence_bundle_manifest`

### Frontend Code Quality
```bash
cd frontend
npm run lint    # 0 errors, 0 warnings
npm run build   # Next.js production build passes for all 18 routes
```

---

## 📋 Hackathon Demo Workflow

1. **Trigger Demo Incident:** Click `Trigger Demo Incident` to seed canonical telemetry (INC-2026-001: Portal 504 Gateway Timeout).
2. **Network Topology & Hardware Check:** Inspect the Service Graph and Physical Campus Hardware Digital Twin to verify network layers are healthy.
3. **Run Autonomous Diagnostics:** Click `Run Next Diagnostic Tool` to execute network-first diagnostic rounds (Switch health, DNS query latency, DB connection pool checks).
4. **Evaluate Competing Hypotheses:** Observe real-time confidence score updates identifying connection pool exhaustion (`max_connections = 50`) caused by recent commit `v2.4.1`.
5. **Human Approval Gate:** SRE operator reviews the generated remediation plan, adds authorization notes, and clicks `Approve Action`.
6. **Execution Confirmation:** Confirm the execution via the safety confirmation dialog.
7. **SLA Verification:** Observe real-time verification across 4 SLA metrics with telemetry latency dropping from 4,200ms to 112ms and error rate dropping to 0.02%.
8. **Synthetic Failure & Replanning Loop:** Test the `Inject Failure & Replan` button to witness autonomous fallback and replanning.

---

## 📄 License

Developed for the TCS Hackathon — Autonomous Incident Investigation & Recovery Agent Challenge.
