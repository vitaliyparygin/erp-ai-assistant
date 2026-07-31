"""
Prometheus metrics for the ERP AI Assistant.
Tracks request rates, latencies, token usage, and agent performance.
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# =============================================================================
# Application Info
# =============================================================================

APP_INFO = Info(
    "erp_assistant_info",
    "ERP AI Assistant application metadata",
)

# =============================================================================
# HTTP Metrics
# =============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "erp_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "erp_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "path"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# =============================================================================
# RAG / Retrieval Metrics
# =============================================================================

RETRIEVAL_REQUESTS_TOTAL = Counter(
    "erp_retrieval_requests_total",
    "Total vector retrieval requests",
    labelnames=["status"],  # success | error
)

RETRIEVAL_LATENCY_SECONDS = Histogram(
    "erp_retrieval_latency_seconds",
    "Vector retrieval latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)

RETRIEVAL_CHUNKS_RETURNED = Histogram(
    "erp_retrieval_chunks_returned",
    "Number of chunks returned per retrieval",
    buckets=[0, 1, 3, 5, 10, 15, 20],
)

# =============================================================================
# LLM / Token Metrics
# =============================================================================

LLM_TOKENS_TOTAL = Counter(
    "erp_llm_tokens_total",
    "Total LLM tokens consumed",
    labelnames=["model", "type"],
)

LLM_REQUESTS_TOTAL = Counter(
    "erp_llm_requests_total",
    "Total LLM API calls",
    labelnames=["model", "agent", "status"],
)

LLM_LATENCY_SECONDS = Histogram(
    "erp_llm_latency_seconds",
    "LLM API call duration in seconds",
    labelnames=["model", "agent"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

# =============================================================================
# Agent / Graph Metrics
# =============================================================================

AGENT_EXECUTIONS_TOTAL = Counter(
    "erp_agent_executions_total",
    "Total agent node executions",
    labelnames=["agent", "status"],  # status: success | error | retry
)

AGENT_LATENCY_SECONDS = Histogram(
    "erp_agent_latency_seconds",
    "Agent execution duration in seconds",
    labelnames=["agent"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

GRAPH_EXECUTIONS_TOTAL = Counter(
    "erp_graph_executions_total",
    "Total LangGraph pipeline executions",
    labelnames=["status"],
)

GRAPH_LATENCY_SECONDS = Histogram(
    "erp_graph_latency_seconds",
    "Full graph execution duration in seconds",
    buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

# =============================================================================
# Document Ingestion Metrics
# =============================================================================

DOCUMENTS_INGESTED_TOTAL = Counter(
    "erp_documents_ingested_total",
    "Total documents ingested",
    labelnames=["status", "mime_type"],
)

INGESTION_CHUNKS_CREATED = Histogram(
    "erp_ingestion_chunks_created",
    "Number of chunks created per document ingestion",
    buckets=[10, 50, 100, 250, 500, 1000, 2500],
)

INGESTION_LATENCY_SECONDS = Histogram(
    "erp_ingestion_latency_seconds",
    "Document ingestion pipeline duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# =============================================================================
# Evaluation Metrics
# =============================================================================

RAGAS_SCORES = Histogram(
    "erp_ragas_scores",
    "RAGAS evaluation scores",
    labelnames=["metric"],  # answer_relevancy | faithfulness | context_precision
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# =============================================================================
# Active Sessions
# =============================================================================

ACTIVE_SESSIONS = Gauge(
    "erp_active_sessions",
    "Number of currently active conversation sessions",
)
