# Visanté AI Engine

Production-ready AI backend for clinical triage and guideline retrieval. Provides a REST API for guided triage flows and RAG over the **Ghana Standard Treatment Guidelines (7th Edition, 2017)**.

---

## Features

- **AI Triage** — Start a session, answer structured questions (chief complaint, duration, severity, fever, breathing, etc.), receive severity level and care recommendations. Powered by Gemini for question generation and risk analysis.
- **RAG over Ghana STG** — Query the guidelines with natural language; get answers with source citations (document name + page). Optional LLM synthesis or raw chunk retrieval.
- **REST API** — JSON over HTTP under `/api/v1` with OpenAPI docs at `/docs` and `/redoc`.
- **Health & observability** — Health check (`/api/v1/status`), test endpoint, and in-memory log buffer for recent logs.
- **Deploy-ready** — Render blueprint (`render.yaml`), Dockerfile, and environment-based config for local, staging, and production.

---

## Tech stack

| Layer        | Technology                          |
|-------------|--------------------------------------|
| API         | FastAPI, Pydantic                    |
| LLM         | Google Gemini (google-genai)         |
| Vector DB   | ChromaDB                             |
| Embeddings  | sentence-transformers / text-embedding-004 |
| PDF         | PyPDF (for guideline ingestion)      |

---

## Prerequisites

- **Python 3.11+**
- **Google AI API key** — [Get one](https://aistudio.google.com/apikey) (used for Gemini: triage questions and RAG synthesis)

---

## Quick start

### 1. Clone and enter the project

```bash
git clone https://github.com/SEYDINA04/visanteaiengine.git
cd visanteaiengine
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set:

- **`GOOGLE_API_KEY`** — Your Gemini API key (required for triage and RAG).

Optional overrides (see `.env.example`): `ENVIRONMENT`, `DEBUG`, `CHROMA_PERSIST_DIRECTORY`, `RAG_TOP_K`, `BASE_URL`.

### 5. Run the server

**Option A — Development (auto-reload):**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Option B — Using the entry script:**

```bash
python main.py
```

Then open:

- **API root:** http://localhost:8000  
- **Swagger UI:** http://localhost:8000/docs  
- **ReDoc:** http://localhost:8000/redoc  
- **Health check:** http://localhost:8000/api/v1/status  

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google AI / Gemini API key ([get key](https://aistudio.google.com/apikey)). Alternatively use `GEMINI_API_KEY`. |
| `BASE_URL` | No | Base URL for docs/reference (e.g. `https://visante-ai-engine.onrender.com`). |
| `ENVIRONMENT` | No | `development`, `staging`, or `production`. Default: `development`. |
| `DEBUG` | No | Enable debug logging. Default: `false`. |
| `CHROMA_PERSIST_DIRECTORY` | No | Chroma persistence path. Default: `./data/chroma`. |
| `RAG_TOP_K` | No | Number of chunks to retrieve for RAG (1–20). Default: `5`. |

See `.env.example` for the full list and comments.

---

## API overview

Base path: **`/api/v1`**

| Area | Endpoint | Method | Description |
|------|----------|--------|-------------|
| System | `/status` | GET | Health check (service name, status, version). |
| System | `/test` | GET | Simple connectivity test. |
| System | `/log` | GET | Recent in-memory log entries (query param: `limit`). |
| Triage | `/triage/start` | POST | Start triage session; returns `session_id` and first question. |
| Triage | `/triage/answer` | POST | Submit answer; returns next question or final outcome (emergency/completed). |
| Triage | `/triage/result/{session_id}` | GET | Full triage report (after session ended). |
| RAG | `/rag/query` | POST | Query Ghana STG; returns answer with source citations. |

- **Interactive docs:** `/docs` (Swagger UI) and `/redoc`.  
- **Detailed triage flow:** See [docs/API_TRIAGE.md](docs/API_TRIAGE.md).

### Triage flow (3 steps)

1. **Start** — `POST /api/v1/triage/start` (optional body: `patient_id`, `language`, `channel`).  
2. **Answer** — Repeated `POST /api/v1/triage/answer` with `session_id`, `question_id`, and `answer` until triage ends (`emergency` or `completed`).  
3. **Result** — `GET /api/v1/triage/result/{session_id}` for the full report (severity, recommendation, risk flags, etc.).

### RAG query

- **POST** `/api/v1/rag/query` with JSON body: `{ "query": "How to treat uncomplicated malaria?", "top_k": 5, "use_llm_synthesis": true }`.  
- Response includes `answer` and `sources` (document name + page).

---

## Project structure

```text
visanteaiengine/
├── app/
│   ├── api/           # REST route handlers (status, triage, rag)
│   ├── core/          # Config, LLM, embeddings, vectorstore, session store, logging
│   ├── rag/           # RAG manager, retriever, indexer, embeddings, reranker
│   ├── triage/        # Triage state machine, question generator, risk analyzer, models
│   └── main.py        # FastAPI app and lifespan
├── data/              # Chroma DB and source documents (e.g. Ghana STG PDF/sample)
├── docs/              # API documentation (e.g. API_TRIAGE.md)
├── scripts/           # Utilities (e.g. run_indexer for ingesting guidelines)
├── tests/             # Pytest tests
├── main.py            # Entry point (uvicorn or python main.py)
├── requirements.txt
├── render.yaml        # Render Blueprint
├── Dockerfile
├── .env.example
└── DEPLOY.md          # Deploying to Render (Blueprint, manual, Docker)
```

---

## RAG: indexing guidelines

To (re)build the vector index from the Ghana STG PDF:

```bash
python scripts/run_indexer.py
```

Config (e.g. source path, collection name) is driven by `app/core/config.py` and env vars. Chroma data is stored under `CHROMA_PERSIST_DIRECTORY` (default `./data/chroma`).

---

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Run with verbose output:

```bash
pytest -v
```

---

## Deployment (Render)

The app is set up for [Render](https://render.com) with:

- **Git repo:** https://github.com/SEYDINA04/visanteaiengine  
- **Render host (example):** https://visante-ai-engine.onrender.com  

Steps:

1. Push code to GitHub (or connect the repo in Render).  
2. Create a **Web Service** (or use a **Blueprint** with `render.yaml`).  
3. Set **Build Command:** `pip install -r requirements.txt`.  
4. Set **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.  
5. Add **Environment:** `GOOGLE_API_KEY` = your Gemini API key.  
6. Optional: set **Health Check Path** to `/api/v1/status`.

Full instructions (Blueprint, manual setup, Docker) are in **[DEPLOY.md](DEPLOY.md)**.

---

## License

See repository license file (if present).

---

## Links

- [Google AI Studio (API key)](https://aistudio.google.com/apikey)  
- [Render](https://render.com)  
- [FastAPI](https://fastapi.tiangolo.com/)  
- [Ghana Standard Treatment Guidelines](https://www.moh.gov.gh/) (reference for the RAG source document)
