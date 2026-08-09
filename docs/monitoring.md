# Monitoring

The AI ERP Assistant includes application-level observability based on Prometheus metrics and Grafana dashboards.

The monitoring stack is intended to provide visibility into:

- HTTP traffic and API health
- LangGraph agent execution
- RAG retrieval performance
- LLM usage and latency
- RAG quality evaluation
- document ingestion
- conversation memory
- auxiliary RAG signals such as query rewriting and context analysis

## Architecture

The monitoring architecture is:

```text
                    ┌─────────────────────┐
                    │   AI ERP Assistant  │
                    │      FastAPI        │
                    └──────────┬──────────┘
                               │
                         /metrics/
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Prometheus      │
                    │  metrics storage    │
                    └──────────┬──────────┘
                               │
                         PromQL queries
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Grafana       │
                    │     dashboards      │
                    └─────────────────────┘
```

## Metrics

### HTTP
- request rate
- latency p50/p95/p99
- status codes
- paths

### Agents
- execution rate
- latency

### Retrieval
- RPS
- latency p50/p95/p99
- Qdrant latency
- reranking latency
- embedding latency

### LLM
- request rate
- error rate
- latency
- token rate

### Graph
- execution rate
- latency p50/p95/p99

### Ingestion
- ingestion rate
- ingestion latency
- chunks created

### Memory
- summarization rate
- active sessions

## Grafana Dashboard

Explain variables:
- Agent
- Model
- Time range

![screen1.png](docs/img/screen_1.png)
![screen2.png](docs/img/screen_2.png)

## PromQL

Important queries used by dashboard.

## Alerts

List configured alerts and thresholds.

## Troubleshooting

### Grafana shows No data

Check that the backend is running:

`docker compose ps backend`

Check the metrics endpoint:

`curl http://localhost:8000/metrics/`

The response should contain Prometheus metrics such as:

`erp_http_requests_total
erp_http_request_duration_seconds
erp_retrieval_requests_total
erp_llm_requests_total
erp_agent_executions_total`

If a particular panel still shows No data, generate traffic that exercises the corresponding feature.

For example:

* ingestion panels → upload a document
* retrieval panels → send RAG chat requests
* LLM panels → execute chat requests
* memory panels → use multi-turn conversations
* RAGAS panels → run evaluation that records RAGAS scores
* Prometheus target is DOWN

Open:

`http://localhost:9090/targets`

Find:

`erp-backend`

The target should be:

`UP`

Check the Prometheus configuration:

`docker/prometheus/prometheus.yml`

Expected target:

```
targets:
  - backend:8000
```
Expected metrics path:

`metrics_path: /metrics/`

Restart Prometheus after configuration changes:

docker compose restart prometheus
### /metrics does not work

Use:

`curl http://localhost:8000/metrics/`

rather than:

`curl http://localhost:8000/metrics`

The application exposes the canonical metrics endpoint with the trailing slash.

### Grafana cannot query Prometheus

Check:

`docker compose ps prometheus grafana`

Then verify Prometheus directly:
`
http://localhost:9090`

Grafana should use the Prometheus datasource configured by the Docker provisioning files.

### Dashboard panels remain empty

A metric only exists in a useful form after the corresponding code path has executed.

For example, an empty ingestion panel does not necessarily indicate a monitoring failure. It may simply mean that no document was ingested during the selected time range.

Check the raw metric:

`curl http://localhost:8000/metrics/ | grep erp_ingestion`

Similarly:

`curl http://localhost:8000/metrics/ | grep erp_retrieval
curl http://localhost:8000/metrics/ | grep erp_llm
curl http://localhost:8000/metrics/ | grep erp_memory`
High latency

Use the dashboard to isolate the slow stage:
`
HTTP
  ↓
Graph
  ↓
Agent
  ↓
RAG stages
  ├── Query rewrite
  ├── Embedding
  ├── Qdrant
  ├── Reranking
  └── Context analysis
  ↓
LLM`

This allows application-level latency to be decomposed instead of treating the entire chat request as a single opaque operation.