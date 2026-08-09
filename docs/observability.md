# Observability
The AI ERP Assistant includes an observability layer based on Prometheus and Grafana.

The monitoring subsystem collects application-level metrics from the FastAPI backend and exposes them through the Prometheus /metrics/ endpoint. Prometheus scrapes these metrics, while Grafana provides dashboards for monitoring HTTP traffic, retrieval, agents, LLM calls, RAG quality, ingestion, and memory operations.

The observability layer is designed primarily for:

local development;
performance debugging;
identifying bottlenecks in the RAG pipeline;
monitoring LangGraph agent execution;
monitoring LLM latency and token consumption;
detecting retrieval failures;
validating application behavior under test traffic.

## Architecture
The observability architecture is based on the following flow:

                         ┌─────────────────────┐
                         │      Grafana        │
                         │                     │
                         │ Dashboards / Panels │
                         └──────────┬──────────┘
                                    │
                              PromQL queries
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     Prometheus      │
                         │                     │
                         │ Time-series storage │
                         └──────────┬──────────┘
                                    │
                              HTTP scrape
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   FastAPI Backend   │
                         │                     │
                         │     /metrics/       │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
        HTTP requests          RAG pipeline          LangGraph
              │                     │                  agents
              │                     │                     │
              ▼                     ▼                     ▼
         HTTP metrics        Retrieval/RAG metrics   Agent metrics
                                    │
                                    ▼
                              LLM / Qdrant
                                    │
                                    ▼
                              LLM / DB metrics

## Metrics
The application exposes metrics for several layers of the system.

The main metric groups are:
* HTTP
* Retrieval
* Agent / LangGraph
* LLM
* RAG
* Ingestion
* Memory


Additional metrics cover reranking, embeddings, Qdrant searches, 
query rewriting, context analysis, document disambiguation,
retrieval-empty events, and active sessions.



### HTTP metrics
HTTP metrics describe the external behavior of the FastAPI application.

They are useful for answering questions such as:

* How many requests are being processed?
* Which endpoints receive the most traffic?
* How many requests fail?
* What is the application latency?
* Which HTTP status codes are returned?

#### HTTP Request Rate

Measures the rate of incoming HTTP requests.

Example:

`HTTP Request Rate
0.16 req/s`

The dashboard can split the rate by HTTP status class or other labels.

Typical interpretation:

`0.16 req/s`

means that the application receives approximately 0.16 requests per second during the selected Prometheus rate interval.

#### HTTP Latency

Shows request latency percentiles.

The dashboard uses:

* p50 — median latency;
* p95 — latency below which 95% of requests fall;
* p99 — latency below which 99% of requests fall.

For example:

`p50 = 100 ms
p95 = 500 ms
p99 = 1 s`

means that most requests are fast, while the slowest requests can take significantly longer.

Percentiles are more useful than average latency for backend monitoring because a small number of very slow requests can otherwise be hidden by the average.

#### HTTP p95

The HTTP p95 panel provides a compact view of the 95th percentile request latency.

For example:

`HTTP p95
30.000 s`

is a warning sign rather than a healthy baseline for a typical API endpoint.

A high p95 can indicate:

* slow LLM requests;
* slow retrieval;
* overloaded services;
* blocking I/O;
* long-running agent execution;
* external service latency.

#### HTTP Requests by Status

Shows requests grouped by HTTP status code.

Typical values include:

`200
307
404
422
500`

For example:

* 200 — successful request;
* 307 — temporary redirect;
* 404 — resource not found;
* 422 — request validation error;
* 500 — internal server error.

The status distribution is useful for detecting API regressions.

#### HTTP Requests by Path

Shows which API endpoints receive traffic.

Typical endpoints include:

`/api/v1/chat/
/metrics
/metrics/`

This makes it possible to determine whether traffic is reaching the expected application endpoints.

### Retrieval metrics

Retrieval metrics describe the RAG retrieval stage.

The retrieval pipeline can be viewed as:

`User query
    │
    ▼
Query processing
    │
    ▼
Embedding
    │
    ▼
Qdrant search
    │
    ▼
Reranking
    │
    ▼
Selected chunks`

The monitoring layer tracks performance and behavior of these steps.

#### Retrieval RPS

Measures the rate of retrieval operations.

Example:

`Retrieval RPS
0.08 requests/sec`

This confirms that retrieval operations are actually being executed.

A value of zero while HTTP traffic is active may indicate that:

* the request did not reach the retrieval stage;
* the agent decided retrieval was unnecessary;
* the retrieval instrumentation is not being triggered;
* the query failed before retrieval.
#### Retrieval Latency

Shows retrieval latency percentiles:

`p50
p95
p99
`
For example:

`p50 = 100 ms
p95 = 800 ms
p99 = 950 ms`

This helps identify whether retrieval is contributing significantly to end-to-end latency.

#### Average Chunks Returned

Shows the average number of chunks returned by retrieval.

Example:

`Average Chunks Returned
4`

This is important for understanding the actual retrieval behavior.

For example:

`0 chunks`

may indicate a retrieval failure or no relevant documents.

While:

`50+ chunks`

could indicate that the retrieval stage is returning too much context.

#### Retrieval Empty Rate

Tracks cases where retrieval returns no relevant chunks.

Example:

`Retrieval Empty Rate
0.000 req/s`

A consistently high value would be a significant RAG-quality signal.

Possible causes include:

* bad embeddings;
* incorrect chunking;
* insufficient document coverage;
* poor query formulation;
* overly strict retrieval thresholds;
* Qdrant search problems.

#### Reranking p95

Measures the 95th percentile latency of the reranking stage.

Example:

`Reranking p95
9.5 ms`

A low value indicates that reranking is not currently a significant bottleneck.

#### Qdrant Search p95

Measures Qdrant search latency.

Example:

`Qdrant Search p95
39 ms`

This isolates the vector database from the rest of the retrieval pipeline.

If:

`Retrieval p95 = 900 ms
Qdrant p95 = 40 ms`

then Qdrant is unlikely to be the primary bottleneck. The remaining latency must come from other retrieval stages.

#### Embedding p95

Measures embedding generation latency.

Example:

`Embedding p95
233.5 ms`

Embedding generation can become an important bottleneck when every query requires a new embedding.
### Agent metrics

The AI ERP Assistant uses a LangGraph-based multi-agent pipeline.

The current architecture contains agents such as:

`Retriever
Research
Summarizer`

Agent-level metrics make it possible to inspect each stage independently.

#### Agent Execution Rate

Shows how often each agent executes.

Example:

`research
retriever
summarizer`

This is useful for validating the actual LangGraph execution path.

For example, if the expected flow is:

`retriever → research → summarizer`

the dashboard should show executions for those agents when a request requiring the complete pipeline is processed.

#### Agent Latency

Shows latency for individual agents.

Example:

`research    8.5 s
retriever  12.0 s
summarizer  13.0 s`

This allows bottleneck identification at the agent level.

If:

`retriever = 500 ms
research  = 8 s
summarizer = 500 ms`

then optimizing Qdrant would probably have little effect on total request latency.

The research agent is the dominant bottleneck.

#### Graph Latency

Measures the latency of the LangGraph execution.

The dashboard can show:

`p50
p95
p99`

This provides a high-level view of the complete graph execution rather than an individual agent.

#### Graph Execution Rate

Tracks successful or completed graph executions.

This metric is useful for detecting situations where:

`HTTP requests > Graph executions`

which may indicate that requests are failing before graph execution.

### LLM metrics
LLM metrics monitor calls to the language model.

This is especially important because LLM calls are often the most expensive and slowest component of an AI application.
#### LLM Request Rate

Measures how often the application sends requests to the LLM.

The metric can be grouped by agent.

For example:

`research
retriever
summarizer`

This helps identify which agent is responsible for most LLM traffic.

#### LLM Error Rate

Tracks failed LLM requests.

A healthy system should normally show:

`0%`

or a very low error rate.

Possible causes of elevated error rates:

* model unavailable;
* Ollama unavailable;
* request timeout;
* invalid request;
* context too large;
* model runtime failure.
* 
#### LLM Latency p95 by Agent

Shows LLM latency separately for each agent.

This is useful because different agents can have very different prompts and workloads.

For example:

`research     8.5 s
retriever   12.0 s
summarizer  13.0 s`

This allows optimization to focus on the actual expensive stage.

#### LLM Token Rate

Measures generated/input token activity.

Token metrics are important for:

* estimating model workload;
* detecting unexpectedly large prompts;
* comparing agents;
* estimating future LLM costs if a hosted model is used.

### RAG metrics
RAG metrics focus on the quality of the retrieval-augmented generation process.

#### RAGAS Scores

The dashboard includes RAGAS-related metrics such as p50 scores.

The goal is to monitor dimensions such as:

* retrieval quality;
* answer relevance;
* faithfulness;
* context quality.

Unlike latency metrics, RAGAS metrics are quality metrics, not infrastructure metrics.

They should generally be evaluated together with retrieval metrics.

For example:

`Retrieval latency ↑
RAGAS score ↓`

may indicate that retrieval is becoming slower while also producing worse context.

#### Context Analysis

Tracks the result of context sufficiency analysis.

Example labels:

`needs_research
sufficient`

This is useful for monitoring the agent's decision-making.

A high `needs_research` rate may indicate that retrieved context is frequently insufficient to answer queries directly.

#### Context Analysis Rate

Measures how often context analysis is performed.

This can be correlated with:

* retrieval requests;
* research-agent executions;
* LLM calls.


### Ingestion metrics

Ingestion metrics monitor document processing.

The expected pipeline is approximately:

`PDF
 │
 ▼
Parsing
 │
 ▼
Chunking
 │
 ▼
Embedding
 │
 ▼
Qdrant`

#### Document Ingestion Rate

Measures how quickly documents are being processed.

If the dashboard displays:

`No data`

while no ingestion is happening, this is expected.

It becomes important when actual document ingestion traffic is generated.

#### Ingestion Latency p95

Measures the 95th percentile latency of document ingestion.

This can reveal slow:

* PDF parsing;
* chunking;
* embedding;
* Qdrant insertion.
#### Average Chunks Created

Shows the average number of chunks generated per document.

For example:

`Average Chunks Created
25`

can help identify unexpected chunking behavior.

If a document that normally creates 20–30 chunks suddenly creates 500 chunks, the chunking configuration may need investigation.

### Memory metrics

Memory metrics monitor conversation-memory operations.

The current dashboard contains memory summarization metrics.

#### Memory Summarization Rate

Measures how often conversation memory is summarized.

A value of:

`No data`

means that no summarization events occurred during the selected time range.

This is not necessarily an error.

#### Memory Summarization Latency

Measures how long memory summarization takes.

This is useful because summarization normally requires an LLM call and can therefore become a noticeable source of latency.

####vActive Sessions

Shows the number of currently active sessions.

For local testing it is normal to see:

`Active Sessions
0`

when no user sessions are active.

## Prometheus

Prometheus is responsible for collecting application metrics.

The FastAPI application exposes metrics through:

`http://backend:8000/metrics/`

Prometheus periodically scrapes this endpoint.

The configured target should appear as:

`erp-backend
UP`

The important distinction is:

`FastAPI
   │
   │ exposes metrics
   ▼
/metrics/
   │
   │ scraped by
   ▼
Prometheus
   │
   │ queried by
   ▼
Grafana`

Prometheus stores the time-series data required by Grafana.


## Grafana

Grafana provides visualization and dashboards on top of Prometheus.

The Grafana datasource is configured to use Prometheus.

The dashboards are stored in:

`docker/grafana/dashboards/`

The dashboard can be filtered by variables such as:

`Agent
Model`

This makes it possible to inspect the behavior of a specific agent or model instead of looking only at aggregated application metrics.

## Dashboard

The main observability dashboard is organized around several layers.

#### Application
`HTTP Request Rate
HTTP Latency
HTTP Requests by Status
HTTP Requests by Path
HTTP p95
HTTP Error Rate`

#### Retrieval
`Retrieval RPS
Retrieval Latency
Average Chunks Returned
Retrieval Empty Rate
Reranking p95
Qdrant Search p95
Embedding p95`

#### Agents
`Agent Execution Rate
Agent Latency
Graph Execution Rate
Graph Latency`

#### LLM
`LLM Request Rate
LLM Error Rate
LLM Latency
LLM Token Rate`

#### RAG
`RAGAS Scores
Context Analysis
Context Analysis Rate
Query Rewrite`
#### Ingestion
`Document Ingestion Rate
Ingestion Latency p95
Average Chunks Created`
#### Memory
`Memory Summarization Rate
Memory Summarization Latency
Active Sessions`

The dashboard should be used primarily to answer:

`Where is the time going?
`
and:

`Where is the pipeline failing or producing poor results?`

## Local development

Start the observability stack together with the application:

`docker compose up --build`

The main services are:

`backend
prometheus
grafana
qdrant
redis
postgres
ollama`

The FastAPI backend exposes:

`/metrics/`

Prometheus collects these metrics.

Grafana visualizes them.


## Generating test traffic

The dashboard will show No data for metrics whose corresponding operations have not occurred.

Therefore, after starting the stack, generate representative traffic.

A useful test sequence is:

#### 1. Health check
`curl http://localhost:8000/health`
#### 2. Metrics endpoint
`curl http://localhost:8000/metrics/`
#### 3. Chat requests

Generate several normal chat/RAG requests:

`curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the status of the project?"
  }'`

Repeat with different questions.

#### 4. Retrieval-heavy questions

Use questions that definitely require document retrieval:

`What is the current project status?

Which vendor is associated with the purchase order?

What is the total amount of the invoice?

What are the payment terms in the contract?

Which customer complaint is related to the specific vendor?

What information is available about the CRM opportunity?`
#### 5. Research-heavy questions

Use questions that should require additional research/context analysis:

```Compare the information about the project across the available documents.

Find all documents related to this customer and summarize the important information.

Determine whether the available documents provide enough information to answer this question.

Compare the vendor information from the vendor profile with the related purchase order.
```
#### 6. Generate concurrent traffic

For local load testing, use a small Python script or HTTP load-testing tool to send multiple requests.

For example:

`10–50 requests
multiple queries
multiple sessions
different query types`

The purpose is not to benchmark production performance yet.

The purpose is to verify that:

`HTTP
  ↓
Agent
  ↓
Retrieval
  ↓
Qdrant
  ↓
LLM
  ↓
RAG`

metrics are actually populated.

---

## Troubleshooting

Dashboard shows No data

First check whether the operation has actually happened.

For example:
`
Document Ingestion Rate
No data`

is expected if no documents were ingested during the selected time range.

Similarly:

`Memory Summarization Rate
No data`

is expected if no conversation required summarization.

#### Prometheus target is DOWN

Check Prometheus targets.

The backend target should be:

`erp-backend
UP`

If it is down, check:

`docker compose ps`

and backend logs:

`docker compose logs backend`

Then verify that the backend metrics endpoint is available:
`
curl http://localhost:8000/metrics/`

Inside Docker networking, Prometheus should use the backend service name:
`
http://backend:8000/metrics/`

#### /metrics redirects

The application currently exposes the application metrics endpoint at:

`/metrics/`

while:

`/metrics
`
may return:

`307 Temporary Redirect`

Prometheus should therefore scrape the canonical endpoint:

`http://backend:8000/metrics/`

---
#### Grafana shows data for HTTP but not Retrieval

This usually means that the HTTP request reached the application, but no retrieval metric was recorded.

Check:

1. whether the request actually triggers retrieval;
2. whether the selected agent requires retrieval;
3. whether the retrieval instrumentation is called;
4. Prometheus metric names;
5. Grafana query filters.

---

#### Grafana shows Retrieval data but no Agent data

Check whether the request reaches the LangGraph execution layer.

Compare:
`
HTTP Request Rate`

with:

`Graph Execution Rate`

If HTTP requests exist but graph executions do not, the request may fail before LangGraph execution.

---

#### High HTTP latency

Compare:
`
HTTP p95`

against:

`Agent p95
Retrieval p95
Qdrant p95
Embedding p95
LLM p95`

This allows the bottleneck to be isolated.

For example:

`HTTP p95        30 s
Agent p95       13 s
Qdrant p95      39 ms
Embedding p95   233 ms`

would suggest that Qdrant is not the main problem.

The investigation should move toward the agent/LLM/request orchestration path.

---

## Known limitations

The current observability implementation is primarily intended for local development and diagnostics.

Known limitations include:

* metrics are currently application-level rather than full infrastructure monitoring;
* Prometheus data is intended for local development and may not have long-term retention;
* Grafana dashboards depend on the corresponding Prometheus metrics being generated;
* panels may show No data when no matching operation occurred during the selected time range;
* RAGAS metrics are not necessarily available for every request;
* memory metrics only appear when memory operations are triggered;
* ingestion metrics only appear when document ingestion is executed;
* LLM token metrics depend on the LLM integration exposing the required token information;
* local Ollama performance is not representative of hosted LLM performance;
* the current dashboard is not a production alerting solution;
* thresholds and alert rules still need to be defined for production use;
* metric cardinality should be reviewed before production deployment, especially for labels such as endpoint, agent, model, or session;
* Prometheus and Grafana currently provide monitoring/visualization, but not a complete distributed tracing solution.