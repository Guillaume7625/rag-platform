# Coding-agent prompt

Drop the prompt below into Cursor / Claude Code / Windsurf / any coding agent
to regenerate or extend this monorepo.  It is intentionally strict so the agent
produces a working application on the first pass.

---

You are a Staff Engineer full-stack senior, expert in AI, RAG, FastAPI,
Next.js, Qdrant and production systems.

Your mission is to generate a complete, executable, production-grade RAG
application with the best quality / cost / complexity tradeoff.

## Product

Build a multi-tenant RAG platform that supports:

- document upload and structured parsing
- hybrid dense + sparse indexing with parent/child chunking
- retrieval, reranking and citation-grounded generation
- access control by tenant, role and tags
- a clean web UI
- a clear backend API
- minimal observability and offline evaluation

## Architecture

Frontend
- Next.js 15 + TypeScript + Tailwind + shadcn/ui + TanStack Query

Backend
- FastAPI + Python 3.12 + Pydantic v2 + SQLAlchemy 2.0 + Alembic
- structlog + prometheus-fastapi-instrumentator

Async / queue
- Celery + Redis

Data
- PostgreSQL 16 (metadata, users, ACL, conversations, eval logs)
- Qdrant (dense + sparse vectors with hybrid query + RRF fusion)
- MinIO (raw documents)

Parsing / ingestion
- Docling for structured parsing, Tesseract OCR fallback for scans
- python-magic for MIME detection, boto3 for object storage

Retrieval / ranking
- Embeddings: BAAI/bge-m3
- Reranker: BAAI/bge-reranker-v2-m3
- Hybrid dense + sparse retrieval in Qdrant
- Parent/child chunking
- ACL filters applied **before** generation, not after

Generation
- Provider abstraction (LiteLLM or equivalent)
- Small model by default, large model as fallback
- Answers grounded only in retrieved context
- Citations are mandatory; refuse if context is insufficient

## Pipeline

1. upload document
2. raw bytes stored in MinIO
3. MIME extraction + sha256
4. structured parsing
5. OCR if needed
6. cleaning
7. parent / child chunking
8. dense + sparse embeddings
9. Qdrant indexing
10. user query
11. query routing standard / deep
12. hybrid retrieval
13. reranking
14. context packing
15. citation-grounded generation
16. confidence score
17. logs / traces / metrics

## Hard parameters

- child chunks: 180–260 tokens
- child overlap: 40
- parent chunks: 800–1100 tokens
- retrieval initial top-k: 50
- rerank top-k: 20
- final context top-k: 6

## UI requirements

Pages: login, chat, drag-and-drop upload, document table, document detail,
conversation history, clickable citations, filters by tag/source/date,
indexing state per document.

## Supported documents

PDF, DOCX, PPTX, TXT, Markdown, HTML, CSV, PNG, JPG.

## Document states

uploaded → parsing → chunking → embedding → indexed (or failed)

## ACL

Every chunk indexed in Qdrant must carry:

- chunk_id
- parent_id
- document_id
- document_version_id
- tenant_id
- page
- section_title
- tags
- source_name
- allowed_roles
- created_at
- content

Filter by tenant_id and allowed_roles **inside** the hybrid query, before
fusion.

## Postgres tables

tenants, users, memberships, documents, document_versions,
document_chunks_parent, document_chunks_child, conversations, messages,
retrieval_traces, evaluation_runs, evaluation_cases.

## Endpoints

- POST /auth/login
- GET /auth/me
- POST /documents/upload
- GET /documents
- GET /documents/{id}
- POST /documents/{id}/reindex
- DELETE /documents/{id}
- POST /chat/query
- GET /conversations
- GET /conversations/{id}
- GET /health
- GET /metrics

## /chat/query response shape

```json
{
  "answer": "...",
  "citations": [
    {
      "document_id": "uuid",
      "document_name": "...",
      "page": 12,
      "chunk_id": "uuid",
      "excerpt": "..."
    }
  ],
  "confidence": 0.87,
  "mode_used": "standard",
  "latency_ms": 1420,
  "conversation_id": "uuid",
  "message_id": "uuid"
}
```

## Software requirements

- monorepo, modular code, strong typing
- no empty pseudo-implementations
- truly executable code
- basic unit + integration tests
- complete README, working docker-compose, .env.example, Makefile
- seed data and Alembic migrations

## Layout

```
rag-platform/
├─ apps/
│  ├─ web/
│  └─ api/
├─ workers/
│  └─ ingestion/
├─ packages/
│  └─ shared/
├─ infra/
└─ docs/
```

## Docker compose services

postgres, redis, qdrant, minio, minio-init, api, worker, web, prometheus.

## Generation rules

- print the full tree first
- generate files in a logical order: infra → backend → worker → frontend → tests → README
- no pseudo-code; every external dependency gets a real minimal implementation
- prioritize maintainability
- comment sparingly but usefully

## Success criteria

After generation the project must allow:

- `docker compose up`
- create a user
- upload a document
- index a document
- ask a question and receive an answer with citations
- filter by tenant
- view documents and conversations

Generate the complete application now.
