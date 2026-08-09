# Deployment

## Overview

AI ERP Assistant is deployed as a Docker Compose application.

The development/release environment consists of:

* **Backend** — FastAPI application
* **Worker** — Celery background worker for document ingestion
* **Frontend** — React/Vite application
* **PostgreSQL** — relational database
* **Redis** — Celery broker/result backend
* **Qdrant** — vector database
* **Ollama** — local LLM runtime
* **Prometheus** — metrics
* **Grafana** — monitoring dashboards

The application is intended to run locally or on a Docker host.

---

## Prerequisites

Install the following before starting the application:

* Docker
* Docker Compose
* Ollama
* Git

Python is required for local development and test execution.

The project currently targets **Python 3.12+**.

Verify the installed versions:

```bash
python3 --version
docker --version
docker compose version
ollama --version
```

---

## Environment Configuration

Create the environment file from the project's example configuration if available:

```bash
cp .env.example .env
```

Review the values before starting the application.

Important configuration includes:

```text
DATABASE_URL
REDIS_URL
QDRANT_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
OLLAMA_BASE_URL
EMBEDDING_MODEL
```

Docker Compose services use Docker-internal hostnames such as:

```text
postgres
redis
qdrant
ollama
```

Do not replace these with `localhost` inside container-to-container configuration.

---

## Start the Application

Build and start all services:

```bash
docker compose up --build -d
```

Check the service status:

```bash
docker compose ps
```

Expected core services:

```text
backend
worker
frontend
postgres
redis
qdrant
ollama
```

---

## Verify Backend

Check the API:

```bash
curl http://localhost:8000/
```

The backend API is available at:

```text
http://localhost:8000
```

API documentation is available through FastAPI:

```text
http://localhost:8000/docs
```

---

## Verify Qdrant

Check Qdrant:

```bash
curl http://localhost:6333/collections
```

After at least one document has been successfully ingested, the expected collection is:

```text
erp_documents
```

Verify it directly:

```bash
curl http://localhost:6333/collections/erp_documents
```

A newly created Qdrant volume will initially contain no collections.

This is expected.

The collection is created during document ingestion.

---

## Verify PostgreSQL

Check the container:

```bash
docker compose ps postgres
```

The PostgreSQL service should be healthy.

For a more detailed check:

```bash
docker compose exec postgres pg_isready
```

Expected result:

```text
accepting connections
```

---

## Verify Redis

Check the Redis container:

```bash
docker compose ps redis
```

Verify connectivity:

```bash
docker compose exec redis redis-cli ping
```

Expected result:

```text
PONG
```

Redis is used by Celery for task messaging and result storage.

---

## Verify Ollama

Check the Ollama service:

```bash
curl http://localhost:11434/api/tags
```

Make sure the configured model is available.

For example:

```bash
ollama list
```

If the required model has not been downloaded yet:

```bash
ollama pull <model-name>
```

Use the model configured by `OLLAMA_MODEL` / the corresponding project configuration.

---

## Verify Celery Worker

The worker must register the ingestion task.

Check worker logs:

```bash
docker compose logs worker --tail=100
```

The startup output should contain:

```text
[tasks]
  . app.workers.ingestion_worker.ingest_document
```

The worker should also listen on the `ingestion` queue:

```text
.> ingestion
```

If the task is not registered, document uploads will return `202 Accepted`, but documents will not be ingested.

---

## Document Ingestion

Upload a document through the API:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/document.pdf"
```

The API should return:

```json
{
  "document_id": "...",
  "filename": "document.pdf",
  "status": "pending",
  "task_id": "..."
}
```

The HTTP `202 Accepted` response means that the document was queued for asynchronous ingestion.

It does **not** mean that indexing has already completed.

Monitor the worker:

```bash
docker compose logs -f worker
```

After successful ingestion, verify Qdrant:

```bash
curl http://localhost:6333/collections
```

The collection should contain:

```text
erp_documents
```

---

## Dataset Upload

The repository contains a dataset upload script:

```bash
python3 scripts/upload_dataset.py
```

Before running it, make sure the complete Docker environment is running:

```bash
docker compose up -d
```

Then run:

```bash
python3 scripts/upload_dataset.py
```

Monitor ingestion:

```bash
docker compose logs -f worker
```

After ingestion completes:

```bash
curl http://localhost:6333/collections
```

Then verify:

```bash
curl http://localhost:6333/collections/erp_documents
```

---

## Chat Verification

Once documents have been successfully ingested, test the chat API:

```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"яка сума в інвойсі INT-2024-555?"}'
```

The request should return an answer based on the indexed documents.

If Qdrant returns:

```text
Collection `erp_documents` doesn't exist
```

the vector store has not been initialized yet. Upload and successfully ingest at least one document before testing chat.

---

## Frontend

The frontend is available at:

```text
http://localhost:3000
```

Open:

```text
http://localhost:3000
```

The frontend communicates with the backend API.

---

## Monitoring

Prometheus is available at:

```text
http://localhost:9090
```

Grafana is available at:

```text
http://localhost:3001
```

### Backend Metrics

http://localhost:8000/metrics/

These services are useful for development and observability but are not required for the minimal application functionality.

GRAFANA_PASSWORD:admin

---

## Health Check

Before a release, verify all services:

```bash
docker compose ps
```

Expected core services should be running:

```text
backend
worker
frontend
postgres
redis
qdrant
ollama
```

Then verify:

```bash
curl http://localhost:8000/
curl http://localhost:6333/collections
curl http://localhost:11434/api/tags
docker compose exec postgres pg_isready
docker compose exec redis redis-cli ping
```

---

## Minimal Release Scenario

The following sequence verifies the minimum production-like workflow.

### 1. Start the environment

```bash
docker compose up --build -d
```

### 2. Verify containers

```bash
docker compose ps
```

### 3. Verify Celery registration

```bash
docker compose logs worker --tail=100
```

Confirm that the worker shows:

```text
app.workers.ingestion_worker.ingest_document
```

and:

```text
ingestion
```

### 4. Verify Qdrant

```bash
curl http://localhost:6333/collections
```

An empty collection list is acceptable immediately after deleting the Qdrant volume.

### 5. Upload a test document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@tests/fixtures/<test-document>.pdf"
```

### 6. Wait for ingestion

```bash
docker compose logs -f worker
```

Look for successful ingestion.

### 7. Verify the vector collection

```bash
curl http://localhost:6333/collections
```

Expected:

```text
erp_documents
```

### 8. Test chat

```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"<question about the uploaded document>"}'
```

### 9. Verify frontend

Open:

```text
http://localhost:3000
```

### 10. Run the release checks

```bash
ruff check app tests
mypy app
pytest -q
```

All checks must pass before release.

---

## Troubleshooting

### Qdrant has no collections

Check:

```bash
curl http://localhost:6333/collections
```

If the result is:

```json
{"result":{"collections":[]}}
```

upload and ingest a document.

Do not manually create `erp_documents` unless the application architecture explicitly requires it. The ingestion pipeline is responsible for initializing the collection.

### Celery reports an unregistered task

If logs contain:

```text
Received unregistered task of type 'ingest_document'
```

check worker startup:

```bash
docker compose logs worker --tail=100
```

The worker must show:

```text
[tasks]
  . app.workers.ingestion_worker.ingest_document
```

Also verify:

```bash
docker compose exec worker \
python -c "from app.workers.celery_app import celery_app; import app.workers.ingestion_worker; print(sorted(k for k in celery_app.tasks if 'ingest' in k))"
```

Expected:

```text
['ingest_document']
```

### Documents remain pending

Check:

```bash
docker compose logs worker --tail=200
```

Then verify that:

* the worker is running;
* `ingest_document` is registered;
* the worker listens to the `ingestion` queue;
* Redis is available;
* Qdrant is available;
* the uploaded file exists inside `/app/uploads`.

---

## Current Project Status

The project is currently **in development**.

The release process described in this document represents the minimum verified deployment scenario and should be expanded as production deployment requirements are introduced.
