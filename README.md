# NyaySaathi

> Empowering citizens with verified Indian legal information through AI chat, curated learning, and retrieval-augmented guidance.

## Table of Contents
- [Overview](#overview)
- [Core Features](#core-features)
- [Architecture](#architecture)
- [Backend (FastAPI)](#backend-fastapi)
- [Frontend (React + Vite)](#frontend-react--vite)
- [Local Development Setup](#local-development-setup)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Running with Docker](#running-with-docker)
- [Environment Configuration](#environment-configuration)
- [Key API Endpoints](#key-api-endpoints)
- [Data / RAG Pipeline](#data--rag-pipeline)
- [NyayLens & NyayShala](#nyaylens--nyayshala)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Security & Trust](#security--trust)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---
## Overview
NyaySaathi is an AI-powered legal companion focused on making authentic Indian legal knowledge accessible. It combines:
- Conversation with an AI assistant (streaming + non-stream responses)
- Retrieval of ingested legal documents (planned Qdrant vector search)
- Daily curated legal learning resources (NyayShala)
- Lens-style exploration panels (NyayLens)
- Admin ingestion & corpus management

The goal is high-signal, transparent, citation-backed legal answers—not generic, hallucinated responses.

## Core Features
- 🔌 Pluggable LLM providers (OpenAI GPT-4o-mini, Google Gemini 2.0 Flash)
- 🔄 Server-Sent Events (SSE) live token streaming
- 📥 Document ingestion endpoint for corpus expansion
- 🧩 Embedding + vector store abstraction (Qdrant planned)
- 📚 Daily NyayShala auto-generation & warm cache
- 🔍 NyayLens exploratory legal views
- 🛡️ Auth scaffolding + CORS controls
- 🧪 Structured text splitting & metadata management for RAG

## Architecture
```
+------------------+        +-----------------+        +-----------------------+
| React Frontend   | <--->  | FastAPI Backend | <----> | Vector DB (Qdrant)    |
| Vite / Tailwind  |        | Routers / SSE   |        | Embeddings / Recall   |
+--------+---------+        +---------+-------+        +-----------+-----------+
         |                           |                            |
         |                           |                            |
         |                +----------v----------+         +-------v--------+
         |                | Embedding Service   |         | Redis (cache)  |
         |                | (sentence-transform)|         +----------------+
         |                +----------+----------+
         |                           |
         |                +----------v----------+
         |                | NyayShala Generator |
         |                +---------------------+
```
Key design points:
- Decoupled services via internal `services/` abstractions.
- Pluggable model backends via `llm_client.py`.
- Embedding + vector layers via `embedding.py` + `vector_store.py`.
- Clean router separation for chat, admin, health, auth, lens, shala, client config.

## Backend (FastAPI)
Located in `Backend/app/` with routers under `app/api/routers/`. Startup hook warms the daily NyayShala cache.

Major modules:
- `core/config.py` – settings & CORS origins
- `services/` – ingestion, embedding, vector store, RAG engine, NyayShala generation
- `utils/text_splitter.py` – chunking strategy for documents

### Dependencies
`requirements.txt` includes: FastAPI, Uvicorn, OpenAI, Google Generative AI, Sentence Transformers, Qdrant client, Redis, PDF / DOCX parsers, JWT + Passlib.

## Frontend (React + Vite)
Located in `Frontend/` using React 19, Tailwind CSS, Framer Motion, React Router, Lucide icons, Markdown rendering.

Key components:
- `ChatInterface/Chatbot.jsx` – streaming & rich answer UI
- `NyayShala.jsx` / `NyayLens.jsx` – learning & exploration panels
- `Navbar/Nav.jsx`, `Sidebar/SideBar.jsx` – navigation & layout
- `lib/api.js` – central API base (env-driven)

## Local Development Setup
### Prerequisites
- Python 3.11+ (recommended)
- Node.js 16+ (for Vite; works with newer versions)
- (Optional) Docker Desktop for containerized vector DB / cache

### Backend Setup (Windows PowerShell)
```powershell
cd e:\Hackathons\AIU1\NyaySaathi\Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env  # then edit API keys & CORS
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Optional GPU embedding (before sentence-transformers install):
```powershell
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio
```

### Frontend Setup
```powershell
cd e:\Hackathons\AIU1\NyaySaathi\Frontend
npm install
npm run dev
```
Visit: http://localhost:5173

### Running with Docker
From `Backend/`:
```powershell
docker compose up -d  # Starts Qdrant (6333) and Redis (6379)
```
Then run backend locally (still points to services).

## Environment Configuration
Create `.env` (backend):
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
LLM_PROVIDER=openai          # or gemini
CORS_ORIGINS=http://localhost:5173
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_DB_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379
JWT_SECRET=change_me
```
Frontend `.env.example` supports:
```
VITE_API_BASE=http://localhost:8000/api
```

## Key API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/health/live` | Liveness probe |
| GET    | `/health/ready` | Readiness (LLM + vector) |
| GET    | `/api/health` | Compatibility alias |
| GET    | `/api/chat/stream?query=...` | SSE streaming response |
| POST   | `/api/chat/ask` | Non-stream chat answer |
| POST   | `/api/admin/documents` | Upload & ingest legal document |
| GET    | `/api/nyayshala/daily` | Daily curated learning set (warm cache) |
| GET    | `/api/lens/...` | NyayLens exploration endpoints (varied) |
| POST   | `/api/auth/login` | Authentication (planned/partial) |
| GET    | `/api/client/config` | Client-config bootstrap |

## Data / RAG Pipeline
1. Upload via Admin endpoint (PDF, DOCX, etc.)
2. Parse & normalise (`pypdf`, `python-docx`, `docx2python`)
3. Split into semantic chunks (`utils/text_splitter.py`)
4. Embed chunks (Sentence Transformers)
5. Persist vectors (Qdrant) + metadata (Redis / JSON store)
6. Query pipeline: user question → embeddings → vector similarity → context assembly → LLM answer with citations.

## NyayLens & NyayShala
- **NyayShala**: Daily generated legal learning capsule; warmed at startup (`nyayshala_generator.py`).
- **NyayLens**: Domain/resource focused panels enabling multi-faceted exploration of statutes, procedures, rights.

## Tech Stack
| Layer | Tools |
|-------|-------|
| Backend | FastAPI, Uvicorn, Pydantic, SSE-Starlette |
| LLM / AI | OpenAI API, Google Generative AI |
| Embeddings | sentence-transformers (PyTorch) |
| Vector Store | Qdrant |
| Cache | Redis |
| Auth | JWT (PyJWT) + Passlib bcrypt |
| Frontend | React 19, Vite, Tailwind CSS, Framer Motion, React Router, React Markdown |

## Project Structure
```
NyaySaathi/
├── constitution_rag_structured.jsonl   # Seed legal corpus structure (example)
├── Backend/
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── core/
│       ├── api/routers/
│       ├── services/
│       ├── utils/
│       └── ...
└── Frontend/
    ├── public/
    ├── src/
    │   ├── components/
    │   ├── lib/api.js
    │   ├── App.jsx
    │   └── ...
```

## Development Workflow
1. Create / update `.env` with provider keys.
2. Start vector & cache services (`docker compose up -d`).
3. Run backend (uvicorn) & frontend (Vite dev server).
4. Ingest documents through admin endpoint.
5. Validate retrieval quality (temporary debugging logs / test queries).
6. Iterate on chunking and embedding model if recall is low.
7. Add tests (planned) for ingestion & retrieval path.

Recommended Enhancements:
- Add pytest suite for services (embedding determinism, ingestion idempotency).
- Introduce Alembic + relational store for auth & document metadata (if scaling beyond Redis/JSON).
- Implement rate limiting (e.g., slowapi) and request ID logging.

## Security & Trust
- Only verified Indian legal documents should be ingested.
- Provide citations in AI responses (prepend source doc + section IDs).
- JWT-based auth for admin ingestion and protected endpoints.
- CORS restricted to known frontend origins.
- Consider prompt-injection sanitization for user queries.

## Roadmap
| Phase | Item |
|-------|------|
| Short | Hook up Qdrant retrieval & context injection |
| Short | Implement admin UI for uploads & status |
| Short | Add citation rendering in `AnswerRenderer.jsx` |
| Medium | Add user auth & role-based access (admin vs public) |
| Medium | Multi-provider failover (fallback from Gemini to OpenAI) |
| Medium | Add evaluation harness for answer quality |
| Long | Multilingual (EN + Indic languages) legal support |
| Long | Privacy-preserving analytics & feedback loop |

## Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Commit changes: `git commit -m "feat: add improvement"`
4. Push: `git push origin feature/my-improvement`
5. Open a Pull Request

Guidelines:
- Follow existing modular service pattern.
- Keep endpoints RESTful & predictable.
- Add docstrings to new service classes/functions.
- Prefer small PRs with focused scope.

## License
MIT License (see `LICENSE` if present or add one).

---
### Maintainers / Credits
Original frontend author: Sayoun Parui (`Frontend/README.md`).
Backend architecture evolving under collaborative contributions.

---
### Quick Commands (Reference)
```powershell
# Backend dev
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend dev
npm run dev

# Vector & cache services
cd Backend; docker compose up -d
```

### Support
Open issues for bugs or feature requests. Star the repo if you find it useful.

---
"Made with intent: Accessible, trustworthy legal guidance for everyone."