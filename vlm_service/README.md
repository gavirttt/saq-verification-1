# Site Cleanliness Analysis Service

FastAPI backend that walks a site's image folder, sends each photo to a
locally-hosted, OpenAI-compatible Vision-Language Model, and persists a
structured clean/messy assessment for human review.

## Architecture

```
app/
  api/            FastAPI routers + Pydantic request/response schemas
  services/       Business logic (analysis orchestration, review)
  repositories/   Persistence abstractions (interface in domain, SQLite impl here)
  clients/        External adapters: VLM HTTP client, filesystem image source
  domain/         Pure models, enums, errors, interfaces — no I/O
  core/           Config, logging, exception mapping, DI container
```

Dependency rule: `api -> services -> domain (+ interfaces)`, with
`repositories`/`clients` implementing those interfaces. Nothing is
instantiated at import time; the `Container` is built once in the FastAPI
`lifespan` and injected via `Depends`.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adjust VLM_BASE_URL etc. if needed
```

## Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health`

## Trigger a site analysis

```bash
curl -X POST http://localhost:8000/api/v1/sites/site-42/analyze \
  -H "Content-Type: application/json" \
  -d '{"site_id": "site-42", "site_path": "/data/sites/site-42"}'
```

Response (202 Accepted) includes a job id immediately; processing runs in
the background:

```json
{"id": "job-uuid", "site_id": "site-42", "status": "pending", "total_images": 37, ...}
```

Poll job progress:

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

## Query results

```bash
# All results for a site
curl http://localhost:8000/api/v1/sites/site-42/results

# A single result
curl http://localhost:8000/api/v1/results/{result_id}
```

## Review queue

```bash
# List items pending human review (messy or low-confidence)
curl http://localhost:8000/api/v1/review/pending?site_id=site-42

# Approve the model's verdict
curl -X POST http://localhost:8000/api/v1/review/{result_id} \
  -H "Content-Type: application/json" \
  -d '{"approve": true, "notes": "Confirmed messy, boxes in hallway"}'

# Reclassify (model was wrong)
curl -X POST http://localhost:8000/api/v1/review/{result_id} \
  -H "Content-Type: application/json" \
  -d '{"approve": false, "reclassified_cleanliness": "clean", "notes": "Actually just shadows"}'
```

## Tests

```bash
pip install -r requirements.txt  # includes pytest, pytest-asyncio
pytest
```

`tests/test_orchestrator.py` exercises `AnalysisOrchestrator` entirely
against fakes (`FakeVLMClient`, `FakeResultsRepository`, `FakeJobsRepository`,
`FakeImageSource`) — no network, filesystem, or database — demonstrating
that the service layer only depends on the `domain.interfaces` Protocols.

## Swapping SQLite for Postgres later

Implement `ResultsRepository`/`JobsRepository` (see
`app/domain/interfaces.py`) against Postgres (e.g. via `asyncpg` or
SQLAlchemy async), then change the two lines in `app/core/container.py`
that construct `SQLiteResultsRepository`/`SQLiteJobsRepository`. Nothing in
`services` or `api` needs to change.
