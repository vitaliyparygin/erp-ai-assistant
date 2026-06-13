# AI ERP Assistant - Prompt Collection

## Retriever Agent

User Question:
{query}

Search the available documents and return the most relevant chunks.
Return only factual information from documents.

---

## Research Agent

Question:
{query}

Context:
{context}

Analyze the retrieved information.
Identify facts, relationships, conclusions and possible answers.

---

## Summarizer Agent

Question:
{query}

Context:
{context}

Instructions:

* Answer only using the provided context.
* Do not invent information.
* If information is missing, say so.
* Keep answers concise.
* Prefer bullet points for structured data.
* Return factual answers only.

---

## Query Rewriter

Rewrite the user's query to improve document retrieval.

Requirements:

* Preserve original meaning.
* Expand abbreviations if useful.
* Keep important entities unchanged.

---

## Context Sufficiency Check

Question:
{query}

Context:
{context}

Determine:

1. Is there enough information to answer?
2. Is additional research required?

Return:

{
"sufficient": true|false,
"needs_research": true|false
}

---

## Memory Agent

Conversation History:
{history}

Current Question:
{query}

Create a standalone query if the user references previous entities using:

* he
* she
* it
* they
* this
* that
* його
* її
* це
* той

Return the resolved query.
