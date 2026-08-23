# AI ERP Assistant — Architecture

## Architecture Overview

AI ERP Assistant is an AI-powered backend application designed to answer questions about ERP-related documents and business data. The system combines **Retrieval-Augmented Generation (RAG)**, **LLM-based agents**, and **LangGraph orchestration** to provide context-aware answers based on indexed documents.

The architecture is organized around several independent layers:

* **API layer** — receives client requests and exposes application functionality through FastAPI.
* **Orchestration layer** — coordinates the AI workflow using LangGraph.
* **Retrieval layer** — searches relevant information in the vector database.
* **LLM layer** — generates and processes responses using a local Ollama model.
* **Data layer** — stores vectors, application data, and conversation state.
* **Observability layer** — collects metrics and provides visibility into application behavior.

The design separates infrastructure concerns from AI workflow logic so that individual components can be developed, tested, or replaced independently.

## High-Level Architecture

```text
                         ┌───────────────┐
                         │    Client     │
                         │ Web / API App │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │    FastAPI    │
                         │   API Layer   │
                         └───────┬───────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   LangGraph Workflow   │
                    │                        │
                    │ Retriever → Research   │
                    │      ↓          ↓      │
                    │ Memory → Summarizer    │
                    │              ↓         │
                    │         Citation       │
                    └───────────┬────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
       ┌────────────┐    ┌────────────┐    ┌────────────┐
       │   Qdrant   │    │   Ollama   │    │ PostgreSQL │
       │ Vector DB  │    │    LLM     │    │ App Data   │
       └────────────┘    └────────────┘    └────────────┘
              │
              ▼
       ┌────────────┐
       │ ERP / PDF  │
       │ Documents  │
       └────────────┘
```

## Core Components

### FastAPI

FastAPI is the application's entry point for external clients. It exposes REST API endpoints for interacting with the AI assistant and managing application functionality.

The API layer is responsible for:

* Receiving and validating requests.
* Passing requests to the AI workflow.
* Returning generated responses.
* Providing a stable interface for future frontend or external integrations.

Business and AI orchestration logic should remain outside API route handlers. API endpoints act primarily as a transport layer between clients and the application services.

### LangGraph Workflow

LangGraph is responsible for orchestrating the AI workflow.

Instead of implementing the assistant as a single prompt and LLM call, the application divides the processing pipeline into specialized steps. Each node in the graph has a focused responsibility and operates on shared workflow state.

The workflow can include the following responsibilities:

* **Retriever** — finds relevant documents and context.
* **Research** — analyzes retrieved information and prepares additional context.
* **Memory** — manages conversation context.
* **Summarizer** — produces a concise and coherent answer.
* **Citation** — associates the response with supporting source information.

This approach makes the workflow easier to observe, test, and extend than a monolithic AI service.

### Retrieval-Augmented Generation

The RAG pipeline allows the assistant to generate answers based on indexed ERP documents rather than relying exclusively on the knowledge of the language model.

The general retrieval process is:

1. A user sends a question.
2. The question is converted into an embedding.
3. Relevant document chunks are retrieved from Qdrant.
4. Retrieved context is passed to the AI workflow.
5. The LLM generates an answer using the available context.
6. Source information can be attached to the final response.

This architecture helps reduce unsupported answers and enables the assistant to work with private or domain-specific ERP information.

### Qdrant

Qdrant is used as the vector database for semantic document search.

During document ingestion, documents are parsed, split into chunks, converted into embeddings, and stored in Qdrant together with relevant metadata.

At query time, the system performs semantic similarity search to retrieve the most relevant chunks.

### Ollama

Ollama provides local LLM inference for the application. Using a local model makes it possible to develop and run the assistant without requiring every request to be sent to an external LLM provider.

The LLM is used by the LangGraph workflow for tasks such as:

* Understanding user questions.
* Processing retrieved context.
* Generating final answers.
* Summarization and reasoning tasks performed by workflow nodes.

The model provider is treated as an infrastructure dependency so that alternative providers can be introduced later without redesigning the entire application.

## Document Ingestion Flow

Documents are processed before they can be used by the RAG pipeline.

```text
Document
    │
    ▼
Parsing
    │
    ▼
Text Extraction
    │
    ▼
Chunking
    │
    ▼
Embedding Generation
    │
    ▼
Qdrant Vector Storage
```

Document metadata is preserved where possible so that retrieved chunks can be associated with their original source.

## Query Processing Flow

A typical user request follows this path:

```text
User Question
      │
      ▼
FastAPI Endpoint
      │
      ▼
LangGraph Workflow
      │
      ├──► Load Conversation Context
      │
      ├──► Retrieve Relevant Documents
      │
      ├──► Analyze Available Context
      │
      ├──► Generate Answer
      │
      └──► Attach Source Information
                │
                ▼
          API Response
```

Each stage has a clear responsibility. This separation is important for debugging and evaluating the quality of the AI pipeline because retrieval failures and generation failures can be analyzed independently.

## Data and Infrastructure

The application uses separate services for different types of data:

| Component  | Responsibility                                 |
| ---------- | ---------------------------------------------- |
| Qdrant     | Vector embeddings and semantic document search |
| PostgreSQL | Application and persistent structured data     |
| Redis      | Caching and asynchronous task infrastructure   |
| Ollama     | Local LLM inference                            |

Keeping these responsibilities separate prevents the AI workflow from depending on a single storage mechanism and makes the infrastructure easier to scale independently.

## Observability

Observability is an important part of the architecture because AI systems can fail in ways that are difficult to diagnose from application logs alone.

The system can collect information about:

* Request latency.
* LangGraph execution time.
* Workflow execution counts.
* Errors and failures.
* Retrieval and generation performance.

Metrics can be exposed to Prometheus and visualized through Grafana.

AI-specific tracing and evaluation tools can also be integrated to analyze prompts, model responses, and workflow execution.

## Architecture Principles

The project follows several architectural principles:

### Separation of Concerns

API handling, AI orchestration, retrieval, persistence, and infrastructure are separated into dedicated components.

### Replaceable Infrastructure

External dependencies such as the LLM provider and vector database should be accessed through application abstractions where practical.

### Observable AI Workflows

The execution of AI workflows should expose enough telemetry to identify performance bottlenecks and failures.

### Evaluation-Driven Development

RAG quality should not be evaluated only through manual testing. Benchmarking and automated evaluation help measure retrieval quality and identify regressions.

### Incremental Evolution

The architecture is designed to support gradual additions such as streaming responses, hybrid search, authentication, MCP integration, and ERP system integrations.

## Future Architecture

The current architecture provides a foundation for several planned improvements:

* Streaming LLM responses.
* Hybrid search combining semantic and keyword retrieval.
* Authentication and user-specific access control.
* MCP and external tool integration.
* Odoo and ERP system integrations.
* A dedicated web or Telegram-based user interface.
* More advanced evaluation and monitoring of AI workflow quality.

These capabilities should be added as extensions to existing boundaries rather than introducing business logic directly into API endpoints or infrastructure services.
