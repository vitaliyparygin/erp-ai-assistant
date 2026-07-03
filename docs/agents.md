# AI Agents

The AI ERP Assistant is built using a multi-agent architecture powered by LangGraph.

Each agent has a single responsibility and communicates with the next stage through a shared state object.

---

# Processing Pipeline

```text
User
  │
  ▼
Memory Agent
  │
  ▼
Retriever Agent
  │
  ▼
Research Agent
  │
  ▼
Summarizer Agent
  │
  ▼
Citation Agent
  │
  ▼
JSON Response
```

---

# Memory Agent

## Purpose

The Memory Agent manages conversation history and provides contextual information required for multi-turn conversations.

Its responsibilities include:

- loading conversation history
- saving user messages
- saving assistant responses
- limiting context window
- providing previous messages to downstream agents

---

## Input

```json
{
  "session_id": "uuid",
  "message": "Who is the contractor?"
}
```

---

## Output

```json
{
  "conversation_history": [
    {
      "role": "user",
      "content": "Who is the contractor?"
    }
  ]
}
```

---

## Pipeline

```text
Receive Request
        │
        ▼
Load Session
        │
        ▼
Load Conversation History
        │
        ▼
Append Current Message
        │
        ▼
Pass Context to Retriever
```

---

## Dependencies

- Conversation Store
- Session Manager
- LangGraph State

---

## Configuration

| Variable | Description |
|------------|-------------|
| MAX_HISTORY | Maximum stored messages |
| SESSION_TTL | Session expiration |

---

## Tests

Covered scenarios:

- create new session
- existing session
- empty history
- long conversations
- session expiration

---

## Failure Modes

- session not found
- corrupted history
- storage unavailable

---

# Retriever Agent

## Purpose

The Retriever Agent performs semantic search over indexed ERP documents.

It retrieves the most relevant document chunks from Qdrant based on the user query.

---

## Input

```json
{
    "question":"Find vendor phone number."
}
```

---

## Output

```json
{
    "chunks":[
        "...",
        "...",
        "..."
    ]
}
```

---

## Pipeline

```text
Question
    │
    ▼
Embedding
    │
    ▼
Qdrant Search
    │
    ▼
Metadata Filter
    │
    ▼
Top-K Results
```

---

## Dependencies

- Qdrant
- Embedding Model
- Metadata Filters

---

## Configuration

| Variable | Description |
|-----------|-------------|
| TOP_K | Retrieved chunks |
| SCORE_THRESHOLD | Minimum similarity |
| COLLECTION | Qdrant collection |

---

## Tests

- semantic search
- metadata filtering
- empty database
- no matches
- duplicate chunks

---

## Failure Modes

- Qdrant unavailable
- embedding failure
- empty collection
- timeout

---

# Research Agent

## Purpose

The Research Agent analyzes retrieved document chunks before they are sent to the language model.

Its responsibilities include:

- validating retrieved context
- removing duplicate chunks
- grouping related documents
- extracting structured metadata
- detecting ambiguous search results
- preparing context for summarization

Unlike the Retriever Agent, this agent does **not** search documents. It improves the quality of retrieved information.

---

## Input

```json
{
    "question":"Who is the contractor?",
    "chunks":[ ... ]
}
```

---

## Output

```json
{
    "context":[ ... ],
    "metadata":[ ... ],
    "needs_disambiguation":true
}
```

---

## Pipeline

```text
Retrieved Chunks
        │
        ▼
Remove Duplicates
        │
        ▼
Metadata Extraction
        │
        ▼
Group Related Documents
        │
        ▼
Disambiguation Check
        │
        ▼
Prepared Context
```

---

## Dependencies

- Retriever Agent
- Metadata Parser
- LangGraph State

---

## Configuration

| Variable | Description |
|-----------|-------------|
| MAX_CONTEXT_DOCUMENTS | Maximum documents |
| REMOVE_DUPLICATES | Enable duplicate removal |
| ENABLE_DISAMBIGUATION | Detect ambiguous queries |

---

## Tests

Covered scenarios:

- duplicate chunks
- multiple contracts
- metadata extraction
- ambiguous questions
- empty retrieval results

---

## Failure Modes

- invalid metadata
- duplicate documents
- missing context
- malformed chunks

---

# Summarizer Agent

## Purpose

The Summarizer Agent generates the final natural language answer using the retrieved context.

It communicates with the Large Language Model and produces concise, factual responses.

---

## Input

```json
{
    "question":"Find vendor phone",
    "context":[ ... ]
}
```

---

## Output

```json
{
    "answer":"Vendor phone number is +380671234567."
}
```

---

## Pipeline

```text
Question
      │
      ▼
Prepared Context
      │
      ▼
LLM Prompt
      │
      ▼
Generate Answer
```

---

## Dependencies

- Ollama
- Qwen
- Prompt Templates

---

## Configuration

| Variable | Description |
|-----------|-------------|
| MODEL | LLM model |
| TEMPERATURE | Response creativity |
| MAX_TOKENS | Maximum output tokens |

---

## Tests

- answer generation
- no context
- hallucination prevention
- multilingual queries

---

## Failure Modes

- LLM unavailable
- timeout
- malformed prompt
- empty answer

---

# Citation Agent

## Purpose

The Citation Agent attaches references to the generated answer.

It ensures every factual response can be traced back to the original ERP documents.

---

## Input

```json
{
    "answer":"...",
    "chunks":[ ... ]
}
```

---

## Output

```json
{
    "answer":"...",
    "citations":[ ... ]
}
```

---

## Pipeline

```text
Generated Answer
        │
        ▼
Match Source Chunks
        │
        ▼
Collect Metadata
        │
        ▼
Generate Citations
```

---

## Dependencies

- Retriever Results
- Metadata
- Document Store

---

## Configuration

| Variable | Description |
|-----------|-------------|
| MAX_CITATIONS | Maximum references |
| INCLUDE_PAGE_NUMBER | Include page number |
| INCLUDE_SCORE | Include similarity score |

---

## Tests

- citation generation
- duplicate citations
- page extraction
- missing metadata

---

## Failure Modes

- missing document metadata
- invalid page number
- orphan chunks
- citation mismatch


# State Object

The AI ERP Assistant uses a shared LangGraph state to exchange data between agents.

Each agent reads only the fields it needs and updates the state with new information for the next processing stage.

---

# Processing Flow

```text
Request
    │
    ▼
Memory Agent
    │
    ▼
Retriever Agent
    │
    ▼
Research Agent
    │
    ▼
Summarizer Agent
    │
    ▼
Citation Agent
    │
    ▼
Response
```

---

# State Lifecycle

```text
User Request
        │
        ▼
+-------------------------+
| question                |
| session_id              |
+-------------------------+

        │

Memory Agent

        │

+-------------------------+
| history                 |
+-------------------------+

        │

Retriever Agent

        │

+-------------------------+
| retrieved_chunks        |
| search_metadata         |
+-------------------------+

        │

Research Agent

        │

+-------------------------+
| filtered_chunks         |
| related_documents       |
| metadata                |
| disambiguation          |
+-------------------------+

        │

Summarizer Agent

        │

+-------------------------+
| answer                  |
| tokens_used             |
| latency_ms              |
+-------------------------+

        │

Citation Agent

        │

+-------------------------+
| citations               |
+-------------------------+

        │

Final JSON Response
```

---

# State Fields

## session_id

Type

```python
str
```

Description

Unique conversation identifier.

Example

```text
6ba1935c-c402-4b5a-8ee8-cec91a7bd99b
```

---

## question

Type

```python
str
```

Description

Original user request.

Example

```text
Who is the contractor?
```

---

## history

Type

```python
list[ChatMessage]
```

Description

Conversation history used by Memory Agent.

Example

```json
[
  {
    "role":"user",
    "content":"Find vendor phone"
  },
  {
    "role":"assistant",
    "content":"Vendor phone is..."
  }
]
```

---

## retrieved_chunks

Type

```python
list[DocumentChunk]
```

Description

Raw search results returned by Qdrant before additional processing.

Contains:

- chunk text
- document id
- similarity score
- metadata

---

## filtered_chunks

Type

```python
list[DocumentChunk]
```

Description

Chunks after duplicate removal and validation.

Produced by Research Agent.

---

## related_documents

Type

```python
list[str]
```

Description

Documents matching the current query.

Example

```text
Purchase Order.pdf

Vendor Agreement.pdf

Service Contract.pdf
```

---

## metadata

Type

```python
dict
```

Description

Extracted structured information from retrieved documents.

Example

```json
{
    "contract_number":"ERP-2026-001",
    "customer":"Alpha LLC",
    "contractor":"ERP Solutions LLC"
}
```

---

## disambiguation

Type

```python
bool
```

Description

Indicates whether multiple documents satisfy the request and user clarification is required.

Example

```python
True
```

---

## answer

Type

```python
str
```

Description

Final answer generated by the Summarizer Agent.

Example

```text
Vendor phone number is +380671234567.
```

---

## citations

Type

```python
list[Citation]
```

Description

Supporting references attached to the final answer.

Example

```json
[
  {
    "document":"Vendor Profile.pdf",
    "page":1,
    "score":0.64
  }
]
```

---

## tokens_used

Type

```python
int
```

Description

Number of LLM tokens consumed during answer generation.

---

## latency_ms

Type

```python
float
```

Description

End-to-end processing time in milliseconds.

---

## agent_trace

Type

```python
dict
```

Description

Execution information collected from every agent.

Useful for:

- debugging
- benchmarking
- performance analysis

Example

```json
{
  "retriever":{
    "latency_ms":45
  },
  "research":{
    "documents":5
  },
  "summarizer":{
    "latency_ms":1080,
    "answer_length":72
  }
}
```

---

# Agent Access Matrix

| State Field | Memory | Retriever | Research | Summarizer | Citation |
|-------------|:------:|:---------:|:---------:|:----------:|:---------:|
| session_id | ✓ | ✓ | ✓ | ✓ | ✓ |
| question | ✓ | ✓ | ✓ | ✓ | ✓ |
| history | ✓ | ✓ | ✓ | ✓ | |
| retrieved_chunks | | ✓ | ✓ | ✓ | ✓ |
| filtered_chunks | | | ✓ | ✓ | ✓ |
| metadata | | | ✓ | ✓ | ✓ |
| disambiguation | | | ✓ | ✓ | |
| answer | | | | ✓ | ✓ |
| citations | | | | | ✓ |
| agent_trace | ✓ | ✓ | ✓ | ✓ | ✓ |
| tokens_used | | | | ✓ | |
| latency_ms | ✓ | ✓ | ✓ | ✓ | ✓ |

---

# State Evolution Example

```text
User
 │
 ▼
question
 │
 ▼
+ history
 │
 ▼
+ retrieved_chunks
 │
 ▼
+ filtered_chunks
 │
 ▼
+ metadata
 │
 ▼
+ answer
 │
 ▼
+ citations
 │
 ▼
JSON Response
```