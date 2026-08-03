# API

## Overview

AI ERP Assistant exposes a FastAPI REST API.

The default local API URL is:

```text
http://localhost:8000
```

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

---

## Document Upload

### Upload a document

```http
POST /api/v1/documents/upload
```

The endpoint accepts a document and queues it for asynchronous ingestion.

### Request

Multipart form-data:

```text
file=<document>
tags=<optional comma-separated tags>
```

Example:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/invoice.pdf"
```

With tags:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/invoice.pdf" \
  -F "tags=finance,invoice"
```

### Response

The endpoint returns HTTP `202 Accepted`.

Example:

```json
{
  "document_id": "d349da2c-e8c3-4f19-b333-7e63d143a4cb",
  "filename": "invoice.pdf",
  "status": "pending",
  "task_id": "b85b6946-ba78-4d3f-84df-584d639cdda3"
}
```

### Important

`202 Accepted` means that the document has been accepted and queued for background processing.

The following operations happen asynchronously:

```text
upload
  ↓
PostgreSQL document record
  ↓
Celery task
  ↓
parse
  ↓
chunk
  ↓
embedding
  ↓
Qdrant indexing
  ↓
document becomes searchable
```

Therefore, a successful upload does not guarantee immediate search availability.

---

## Document Listing

### List documents

```http
GET /api/v1/documents/
```

Example:

```bash
curl http://localhost:8000/api/v1/documents/
```

### Pagination

Supported query parameters include:

```text
page
page_size
```

Example:

```bash
curl "http://localhost:8000/api/v1/documents/?page=1&page_size=20"
```

### Filter by status

The endpoint supports filtering by document status:

```text
doc_status
```

Example:

```bash
curl "http://localhost:8000/api/v1/documents/?doc_status=pending"
```

---

## Chat

### Ask a question

```http
POST /api/v1/chat/
```

Request:

```json
{
  "message": "яка сума в інвойсі INT-2024-555?"
}
```

Example:

```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"яка сума в інвойсі INT-2024-555?"}'
```

The request is processed by the RAG/agent pipeline.

The pipeline uses indexed document data to retrieve relevant context and generate an answer.

### Prerequisite

The Qdrant collection must exist and contain indexed documents.

After a fresh Qdrant installation or after deleting the Qdrant volume, the collection may initially be empty:

```bash
curl http://localhost:6333/collections
```

After successful ingestion:

```text
erp_documents
```

should be present.

---

## Document Lifecycle

Documents move through the ingestion pipeline asynchronously.

Typical flow:

```text
PENDING
   ↓
Celery ingestion task
   ↓
parse
   ↓
chunk
   ↓
embed
   ↓
Qdrant upsert
   ↓
INDEXED
```

If ingestion fails, the document is marked as failed and the Celery task may be retried according to the worker configuration.

---

## Celery Task

Document ingestion is handled by:

```text
app.workers.ingestion_worker.ingest_document
```

The task is registered with Celery as:

```text
ingest_document
```

It is routed to:

```text
ingestion
```

queue.

The worker should therefore show:

```text
[queues]
  .> ingestion
```

and:

```text
[tasks]
  . app.workers.ingestion_worker.ingest_document
```

---

## Supported Documents

The upload endpoint determines the MIME type from the file extension.

Current mappings include:

| Extension | MIME type                                                                 |
| --------- | ------------------------------------------------------------------------- |
| `.pdf`    | `application/pdf`                                                         |
| `.docx`   | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.txt`    | `text/plain`                                                              |
| `.md`     | `text/markdown`                                                           |

The actual allowed extensions are controlled by application settings.

---

## Error Handling

The API uses HTTP errors for invalid requests and application-specific failures.

Examples include:

### Missing filename

```text
400 Bad Request
```

### Unsupported file type

```text
UnsupportedFileTypeError
```

### File exceeds configured limit

```text
FileSizeLimitExceededError
```

### Document does not exist

```text
DocumentNotFoundError
```

### Agent pipeline failure

The chat endpoint may return an error when a downstream component fails.

For example, if Qdrant has not yet been initialized:

```text
Qdrant search failed:
Collection `erp_documents` doesn't exist
```

This indicates an infrastructure/data-state problem rather than an invalid chat request.

---

## Local Service URLs

| Service        | URL                                  |
| -------------- | ------------------------------------ |
| Backend API    | `http://localhost:8000`              |
| Swagger UI     | `http://localhost:8000/docs`         |
| OpenAPI schema | `http://localhost:8000/openapi.json` |
| Frontend       | `http://localhost:3000`              |
| Qdrant         | `http://localhost:6333`              |
| Ollama         | `http://localhost:11434`             |
| Prometheus     | `http://localhost:9090`              |
| Grafana        | `http://localhost:3001`              |

PostgreSQL and Redis are primarily accessed by the application through the Docker network.

---

## Minimal API Verification

### 1. Check backend

```bash
curl http://localhost:8000/
```

### 2. Check Qdrant

```bash
curl http://localhost:6333/collections
```

### 3. Upload a document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/test.pdf"
```

### 4. Monitor ingestion

```bash
docker compose logs -f worker
```

### 5. Verify Qdrant collection

```bash
curl http://localhost:6333/collections
```

Expected after successful ingestion:

```text
erp_documents
```

### 6. Ask a question

```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"<question about the uploaded document>"}'
```

---

## API Documentation

For the complete endpoint schema, request/response models, and available parameters, use the generated FastAPI documentation:

```text
http://localhost:8000/docs
```

The interactive documentation should be treated as the authoritative API contract while the project remains under active development.
