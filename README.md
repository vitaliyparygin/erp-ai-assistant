# AI ERP Assistant

> AI-powered ERP Assistant built with FastAPI, LangGraph, Ollama, Qdrant and Retrieval-Augmented Generation (RAG).

![Python](https://img.shields.io/badge/python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLMs-black)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20Database-red)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker)

### Quality

![Tests](https://img.shields.io/badge/tests-533%20passed-success)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)
![Typing](https://img.shields.io/badge/mypy-enabled-blue)
![Formatter](https://img.shields.io/badge/code%20style-black-000000)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/vitaliyparygin/erp-ai-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/vitaliyparygin/erp-ai-assistant/actions/workflows/ci.yml)

## Overview

AI ERP Assistant is an enterprise Retrieval-Augmented Generation (RAG) platform designed to answer questions over ERP documentation.

Instead of relying on a single prompt, the application orchestrates multiple specialized agents using LangGraph, stores semantic document embeddings in Qdrant, and runs completely on local LLMs through Ollama.

The project focuses on:

 - enterprise document search
 - multi-agent reasoning
 - conversational memory
 - citation-aware answers
 - production-ready backend architecture
 - complete automated testing



## Features

### AI
* Multi-Agent Architecture (LangGraph)
* Retrieval-Augmented Generation (RAG)
* Local LLM support (Ollama)
* Query rewriting
* Semantic search
* Cross-Encoder reranking
* Conversation memory
* Citation generation
* Context-aware responses

### Document Processing
* PDF support
* DOCX support
* TXT support
* Markdown support
* Automatic metadata extraction
* Smart chunking
* Document filtering
* Field extraction using configurable rules

### Backend
* FastAPI
* Async architecture
* SQLAlchemy
* PostgreSQL
* Redis
* Qdrant
* Celery background workers
* Docker deployment

### Quality
* 533 automated tests
* 95% code coverage
* Ruff
* MyPy
* Pytest
* Structured logging
* Prometheus metrics

### Monitoring
* 📊 Observability with Prometheus + Grafana
* 📈 HTTP, RAG, retrieval, agent and LLM metrics
* 🚨 Monitoring and alerting



---

## Architecture

![architecture_diagram.png](docs/img/architecture_diagram.png)




---
##  Quick Start

### Prerequisites

For local development and the Docker-based application stack:

* Docker Desktop with Docker Compose
* Python 3.12+ for local scripts and development
* Git
* At least 8 GB of RAM recommended for the full stack
* Sufficient disk space for Docker images, PostgreSQL data, Qdrant vectors, uploaded documents, and the Ollama model

The application stack includes:

* FastAPI backend
* Celery worker
* PostgreSQL
* Redis
* Qdrant
* Ollama
* React/Vite frontend
* Prometheus
* Grafana

PostgreSQL, Redis, Qdrant, Ollama, the backend, worker, and frontend are started by Docker Compose.

Python is required on the host for development commands and utility scripts such as dataset upload scripts.

### Start the application

```bash
docker compose up --build
```

For subsequent starts, when images do not need to be rebuilt:

```bash
docker compose up
```

Run the stack in the background:

```bash
docker compose up -d
```

Check service status:

```bash
docker compose ps
```

Check backend and worker logs:

```bash
docker compose logs backend --tail=100
docker compose logs worker --tail=100
```

### Python version

The Docker application runtime uses Python 3.12.

Python 3.12+ is recommended for local development and utility scripts.

The host Python version does not have to match the Docker runtime exactly, but the project's Python dependencies and development tools should be compatible with the supported Python version.






## Example
### Document Upload

Documents can be uploaded through the REST API.

Example:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@tests/datasets/Invoice.pdf"
```

The endpoint returns `202 Accepted` and a Celery task ID.

Example response:

```json
{
  "document_id": "...",
  "filename": "Invoice.pdf",
  "status": "pending",
  "task_id": "..."
}
```

Document ingestion runs asynchronously:

```text
upload
  → PostgreSQL document record
  → Celery task
  → parse
  → chunk
  → embeddings
  → Qdrant
  → document indexed
```

Monitor ingestion:

```bash
docker compose logs worker --tail=100
```

For a fresh installation, wait until the dataset has finished indexing before testing chat.

### Load the Example Dataset

The repository contains an example dataset under:

```text
tests/datasets/
```

Upload the dataset using:

```bash
python3 scripts/upload_dataset.py
```

The script uploads the PDF files through the public document upload API.

Monitor the Celery worker:

```bash
docker compose logs -f worker
```

After ingestion completes, verify the Qdrant collection:

```bash
curl http://localhost:6333/collections
```

Then verify:

```bash
curl http://localhost:6333/collections/erp_documents
```

The collection should exist and contain indexed vectors.

The dataset is required for the example RAG chat scenarios documented below.


### Chat

Send a question to the ERP Assistant:

```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "яка сума в інвойсі INT-2024-555?"
  }'
```

The request is processed through the RAG pipeline:

```text
query
  → query processing
  → retrieval from Qdrant
  → reranking
  → context analysis
  → answer generation
  → citations
```

A successful response should contain an answer and, when applicable, document citations.

If Qdrant reports that `erp_documents` does not exist, load or re-index the dataset before testing chat.




---

### API

POST

/api/v1/chat

Example

```json
{
    "message":"How do I create a sales order?"
}
```


## Documentation

Detailed documentation is available in the `docs/` directory.

| Topic                                  | Description                                                                                                                            |
|----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| [Agents](docs/agents.md)               | Multi-agent workflow                                                                                                                   |
| [API](docs/api.md)                     | REST API                                                                                                                               |
| [Architecture](docs/architecture.md)   | System architecture                                                                                                                    |
| [Benchmarks](docs/benchmarks.md)       | Benchmark generation                                                                                                                   |
| [Configuration](docs/configuration.md) | Configuration options                                                                                                                  |
| [Deployment](docs/deployment.md)       | Deployment guide                                                                                                                       |
| [FAQ](docs/faq.md)                     | Frequently asked questions                                                                                                             |
| [Prompts](docs/prompts.md)             | Prompt templates                                                                                                                       |
| [Rag](docs/rag.md)                     | Rag                                                                                                                                    |
| [Examples](docs/examples/)             | Example datasets                                                                                                                       |
| [Roadmap](docs/roadmap.md)             | Roadmap                                                                                                                                |
| [Testing](docs/testing.md)             | Testing                                                                                                                                |
| [Observability](docs/observability.md) | The system exposes Prometheus metrics and provides a Grafana dashboard for monitoring HTTP, agent, retrieval, LLM and RAG performance. |
| [Monitoring](docs/monitoring.md)       | Prometheus and Grafana observability                                                                                                                   |



## Tech Stack

- **Python 3.12+**
- **FastAPI** — REST API
- **LangChain / LangGraph** — LLM and agent orchestration
- **Ollama / Qwen 2.5 7B** — local LLM inference
- **Qdrant** — vector database and semantic retrieval
- **PostgreSQL** — persistent data storage
- **Redis / Celery** — background processing
- **Prometheus / Grafana** — observability and monitoring
- **Docker / Docker Compose** — containerized deployment
- **pytest / mypy / Ruff** — testing and code quality


## Status

### Implemented

* Multi-Agent orchestration with LangGraph
* RAG-based document retrieval
* Local LLM inference with Ollama
* Qdrant vector search
* PostgreSQL persistence
* Redis-backed conversation memory
* Celery-based asynchronous document ingestion
* Document parsing and chunking
* Metadata extraction
* Query rewriting
* Retrieval reranking
* Citation-aware responses
* FastAPI REST API
* React frontend
* Docker Compose deployment
* Health and readiness checks
* Prometheus metrics
* Grafana observability dashboard
* HTTP, RAG, agent and LLM monitoring
* Health and readiness checks
* Automated unit and integration tests
* Ruff and MyPy validation

### Release validation

The current release candidate has passed:

```text

ruff check app tests
mypy app
```
**<!-- TEST_COUNT -->556<!-- TEST_COUNT_END -->** pytest tests

### Experimental

The following scripts are not part of the release validation pipeline:

* `scripts/experimental/e2e_chat.py`
* `scripts/experimental/top_k_tuning.py`
* `scripts/experimental/threshold_tuning.py`

They are intended for evaluation, tuning, and further RAG quality improvements.

### Planned

* Authentication
* Improved streaming UX
* Hybrid search
* MCP integration
* Further frontend improvements
* Odoo integration


## Testing

The project contains **<!-- TEST_COUNT -->556<!-- TEST_COUNT_END -->** automated tests.

Run the test suite:

## License

This project is licensed under the
Vitalii Parygin Agent Platform License (VPAL-1.0).

See [LICENSE.md](LICENSE.md) for the license terms.
