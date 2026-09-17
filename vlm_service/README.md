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
uv sync
cp .env.example .env   # adjust VLM_BASE_URL etc. if needed
```

By default, `uv sync` will create a virtual environment in `.venv` and install all project and development dependencies defined in `pyproject.toml`.

If you prefer to activate the virtual environment manually:
```bash
# On macOS/Linux:
source .venv/bin/activate
# On Windows (Command Prompt):
# .venv\Scripts\activate.bat
# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1
```

## Choosing a VLM provider: local vs. AWS Bedrock

The service supports two interchangeable `VLMClient` implementations,
selected via `VLM_PROVIDER` in `.env`.

**Local, OpenAI-compatible server** (`VLM_PROVIDER=local`, the default):
uses `VLM_BASE_URL` / `VLM_API_KEY` / `VLM_MODEL` / `VLM_HTTP_REFERER` (optional) / `VLM_X_TITLE` (optional). 

**AWS Bedrock** (`VLM_PROVIDER=bedrock`): uses `BEDROCK_MODEL_ID` and
`BEDROCK_REGION`. AWS credentials are **not** set in `.env` — configure
them via `aws configure`, the standard `AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` environment variables, or an
attached IAM role if running on EC2/ECS/Lambda. Before it'll work you also
need to:
1. Enable access to your chosen model in the Bedrock console (Model
   access page) for your account/region — this is a one-time,
   per-account/region approval step separate from IAM.
2. Grant the IAM principal running the app `bedrock:InvokeModel` (and
   `bedrock:Converse`) permission, scoped to the model's ARN.

Example `.env` for Bedrock:
```
VLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_REGION=us-east-1
```

Swapping providers is a config change only — `AnalysisOrchestrator` depends
on the `VLMClient` interface (`app/domain/interfaces.py`), not on either
concrete adapter. See `app/core/container.py` for the single branch point.

## Run the server

```bash
uv run uvicorn app.main:app --reload --port 8000
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
uv run pytest
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
