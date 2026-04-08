# Architecture

## Components

```
Next.js Web ── FastAPI API ── PostgreSQL
                │       │
                │       ├── Qdrant (dense + sparse)
                │       ├── MinIO (raw documents)
                │       └── Redis (cache, broker)
                │
                └── Celery worker (ingestion)
```

## Core principles

- **Multi-tenant by design.** Every document, chunk, and conversation carries
  a `tenant_id`. ACL filters are applied **before** generation, not after.
- **Hybrid retrieval.** Qdrant stores both dense (BGE-M3) and sparse vectors,
  fused via RRF. Improves recall on rare entities and exact matches.
- **Parent / child chunking.** Children (180–260 tokens) are indexed for
  precision; parents (800–1100 tokens) are returned as context for the LLM.
- **Reranking.** Top 50 candidates are reranked with BGE-reranker-v2-m3 down
  to top 6 for the final context window.
- **Router.** A small heuristic router decides between `standard` (single
  retrieval pass) and `deep` (query decomposition + multi-pass retrieval).
- **Provider abstraction.** A single `LLMProvider` shields the rest of the
  app from the choice of model / vendor.
- **Observability.** Prometheus metrics + structlog JSON logs + retrieval
  traces persisted to Postgres for offline evaluation.

## Data flow

### Ingestion

1. API receives upload, persists raw bytes in MinIO, creates `documents` row
   in `uploaded` state.
2. API enqueues `ingestion.parse_document` (Celery / Redis).
3. Worker pulls bytes, parses via Docling (with OCR fallback), produces a
   list of sections.
4. Worker chunks into parents + children, persists to Postgres.
5. Worker embeds children (dense + sparse), upserts into Qdrant with the
   ACL-aware payload.
6. Worker flips `documents.state` to `indexed`.

### Query

1. API receives `POST /chat/query`.
2. `query_router_service` decides standard vs deep.
3. `retrieval_service` runs hybrid Qdrant search with `tenant_id` and
   `allowed_roles` filters.
4. `rerank_service` reranks the candidates.
5. `generation_service` packs parent contexts, calls the LLM, returns the
   answer with citations and a confidence score.
6. The conversation, message, and `retrieval_trace` are persisted.
