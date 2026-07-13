---

# docs/faq.md

````md
# Frequently Asked Questions

## Which LLMs are supported?

Currently the project is designed to work with local Ollama models.

Recommended models:

- Qwen
- Llama
- Mistral

---

## Which document formats are supported?

The ingestion pipeline currently supports:

- PDF
- TXT
- Markdown

Additional readers can be implemented through the ReaderRegistry.

---

## Does the project require internet access?

No.

The default configuration is designed for local execution using:

- Ollama
- Qdrant

---

## Can I use OpenAI instead of Ollama?

Yes.

Only the LLM provider needs to be replaced.

The retrieval pipeline remains unchanged.

---

## Can I use another vector database?

Yes.

The retriever is isolated behind an abstraction layer.

Supported implementations can be added for:

- Qdrant
- pgvector
- Milvus
- Chroma

---

## Is Odoo required?

No.

The AI ERP Assistant is ERP-independent.

Odoo integration is provided as an optional component.

---

## Where should new prompts be stored?

All prompts belong under