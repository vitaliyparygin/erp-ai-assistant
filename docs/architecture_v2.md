# AI ERP Assistant — Architecture V2

> **Status:** Draft
> **Version:** 2.0

## Purpose

This document describes the target architecture of **AI ERP Assistant V2**.

The purpose of the V2 architecture is to provide a clear and maintainable foundation for the next stage of the project. It defines the responsibilities and boundaries of the main application components, the AI workflow, data processing pipelines, and infrastructure services.

Unlike the initial architecture, V2 focuses on making the system easier to evolve, test, observe, and integrate with external ERP systems and AI capabilities.

## Architectural Goals

The V2 architecture should support:

* A clear separation between API, application, AI, and infrastructure layers.
* Reliable and testable AI workflows.
* Retrieval-Augmented Generation based on ERP documents and business knowledge.
* Replaceable LLM and external service providers.
* Observable request and AI workflow execution.
* Incremental integration with ERP systems.
* Future support for tools, MCP, and agent capabilities.

## Scope

This document will define:

1. The high-level system architecture.
2. Application layers and component responsibilities.
3. The AI and RAG processing workflow.
4. Data storage and infrastructure boundaries.
5. Communication between components.
6. Observability and evaluation architecture.
7. Architectural decisions for future development.

Detailed implementation decisions and API specifications are documented separately.

## Architecture Principles

### Clear Boundaries

Each component should have a well-defined responsibility. API endpoints should not contain AI orchestration logic, and infrastructure details should not leak into domain or application logic.

### Provider Independence

The application should avoid coupling its core logic directly to a specific LLM provider, vector database, or external ERP implementation.

### Explicit Workflows

AI processing should be represented as explicit workflows rather than hidden inside large service methods. This makes execution easier to test, monitor, and modify.

### Observability by Design

Metrics, logs, and traces should be considered part of the architecture rather than added only when production problems occur.

### Incremental Complexity

V2 should not introduce distributed or multi-agent complexity unless it provides a clear benefit. The architecture should remain as simple as possible while supporting the project's requirements.

## Document Status

This document is a working architecture specification. The following sections will be expanded as architectural decisions are made and validated against the existing implementation.

## Next Sections

* High-Level Architecture
* Application Layers
* AI Workflow Architecture
* RAG Pipeline
* Data Architecture
* Infrastructure
* Observability
* Security Boundaries
* Architectural Decisions
* Future Evolution
