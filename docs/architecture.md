# CampusOps AI — Architecture Overview

## 1. System Overview

CampusOps AI is an AI-powered campus IT operations and incident resolution platform built as a monorepo with independently runnable frontend and backend services.

```
┌─────────────┐       REST API       ┌─────────────────┐
│   Frontend  │ ◄──────────────────► │    Backend      │
│  (Next.js)  │                      │   (FastAPI)     │
│  Port 3000  │                      │   Port 8000     │
└─────────────┘                      └────────┬────────┘
                                              │
                                     ┌────────┴────────┐
                                     │                  │
                               ┌─────▼─────┐    ┌──────▼──────┐
                               │ PostgreSQL │    │ Google      │
                               │ + pgvector │    │ Gemini API  │
                               └───────────┘    └─────────────┘
```

## 2. Frontend — Next.js

| Aspect          | Choice                                |
| --------------- | ------------------------------------- |
| Framework       | Next.js (App Router)                  |
| Language        | TypeScript                            |
| Styling         | Tailwind CSS                          |
| State Mgmt      | React hooks / Context (initially)    |
| API Client      | Fetch API / lightweight REST wrapper  |

### Responsibilities
- Responsive, accessible UI shell
- User authentication flow (Google Identity Services)
- Dashboard, incident views and AI interaction surfaces
- Client-side form validation

## 3. Backend — FastAPI

| Aspect          | Choice                         |
| --------------- | ------------------------------ |
| Framework       | FastAPI                        |
| Language        | Python 3.13                    |
| Config          | pydantic-settings (.env)       |
| CORS            | Environment-driven origins     |

### Structure
```
backend/
├── app/
│   ├── main.py          # Application entry point
│   ├── config.py         # Environment-based settings
│   ├── routes/           # API endpoint routers
│   │   └── health.py     # Health-check endpoint
│   └── services/         # Business logic (modular)
└── requirements.txt
```

### Responsibilities
- RESTful API serving the frontend
- AI/ML orchestration (Gemini API calls, scikit-learn pipelines)
- Database access layer (PostgreSQL + pgvector)
- Authentication verification
- Modular service layer for domain-specific features

## 4. Database — PostgreSQL + pgvector

| Aspect          | Choice                          |
| --------------- | ------------------------------- |
| Engine          | PostgreSQL                      |
| Vector search   | pgvector extension              |
| ORM / queries   | TBD (SQLAlchemy or asyncpg)     |

### Purpose
- Structured data storage (users, incidents, tickets)
- Vector embeddings for semantic search and AI retrieval
- Schema will be designed after the problem statement is finalized

## 5. AI / ML Layer

| Aspect          | Choice              |
| --------------- | ------------------- |
| LLM             | Google Gemini API   |
| ML              | Scikit-learn        |

### Planned capabilities
- Natural language understanding for incident reports
- Automated classification and routing
- Knowledge base retrieval (RAG with pgvector)
- Predictive analytics (scikit-learn)
- Specific features TBD based on problem statement

## 6. Authentication

| Aspect          | Choice                      |
| --------------- | --------------------------- |
| Provider        | Google Identity Services    |
| Flow            | OAuth 2.0 / OpenID Connect  |
| Token handling  | Backend verification        |

### Flow
1. User signs in via Google on the frontend
2. Frontend sends the ID token to the backend
3. Backend verifies the token with Google
4. Backend issues or validates session

## 7. API Communication

All frontend ↔ backend communication uses **REST over HTTPS**.

| Method | Usage                              |
| ------ | ---------------------------------- |
| GET    | Fetch resources, health checks     |
| POST   | Create incidents, submit queries   |
| PUT    | Update records                     |
| DELETE | Remove records                     |

## 8. Modular Problem-Statement Integration

The architecture deliberately separates domain-specific logic into the `services/` layer. When the official hackathon problem statement arrives:

1. New service modules will be added under `backend/app/services/`
2. Corresponding routes will be added under `backend/app/routes/`
3. Frontend pages/components will be added under `frontend/src/app/`
4. Database schema will be designed to match the domain requirements

This ensures the foundation remains stable while features are layered on top.

## 9. Environment Configuration

All secrets and environment-specific values are loaded from `.env` files (never committed). See `.env.example` for the full list of required variables.

