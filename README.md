# RAG Platform

Production-grade multi-tenant RAG platform with hybrid retrieval, reranking, and citation-grounded generation.

## Stack

- **Frontend**: Next.js 15, TypeScript, Tailwind, shadcn/ui, TanStack Query
- **Backend**: FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic v2, Alembic
- **Async**: Celery + Redis
- **Data**: PostgreSQL 16, Qdrant (dense + sparse), MinIO
- **RAG**: Docling, BGE-M3 embeddings, BGE-reranker-v2-m3, LiteLLM provider abstraction

## Monorepo layout

```
rag-platform/
├─ apps/
│  ├─ web/              # Next.js 15 frontend
│  └─ api/              # FastAPI backend
├─ workers/
│  └─ ingestion/        # Celery ingestion worker
├─ packages/
│  └─ shared/           # Shared schemas / enums / clients
├─ infra/               # Docker compose, env, prometheus, scripts
└─ docs/                # Architecture & pipeline docs
```

## Quickstart

```bash
cp infra/env/api.env.example     infra/env/api.env
cp infra/env/worker.env.example  infra/env/worker.env
cp infra/env/web.env.example     infra/env/web.env

make up            # start docker compose
make migrate       # apply alembic migrations
make seed          # insert demo tenant + user
```

- Web:      http://localhost:3000
- API:      http://localhost:8000/docs
- Qdrant:   http://localhost:6333/dashboard
- MinIO:    http://localhost:9001  (minio / minio123)

Default demo credentials (after `make seed`):
```
email:    demo@rag.local
password: demo1234
```

## Pipeline

See [docs/rag-pipeline.md](docs/rag-pipeline.md).

1. Upload → MinIO
2. Parse (Docling, OCR fallback)
3. Chunk (parent 800-1100 tok / child 180-260 tok, overlap 40)
4. Embed (BGE-M3 dense + sparse)
5. Index (Qdrant, payload with `tenant_id`, `allowed_roles`, etc.)
6. Query → router (standard / deep)
7. Hybrid retrieval (top 50) + ACL filter
8. Rerank (top 20 → 6)
9. Generate with citations (small LLM default, large as fallback)

## Useful commands

```bash
make up          # docker compose up -d
make down        # docker compose down
make logs        # tail all logs
make migrate     # alembic upgrade head
make seed        # seed demo data
make test        # run api + worker tests
make fmt         # format python + ts
make lint        # lint python + ts
```

## Environment

See `.env.example` and `infra/env/*.env.example`.

Key variables:
- `DATABASE_URL`
- `QDRANT_URL`
- `MINIO_*`
- `EMBEDDING_MODEL` (default `BAAI/bge-m3`)
- `RERANKER_MODEL` (default `BAAI/bge-reranker-v2-m3`)
- `LLM_PROVIDER`, `LLM_SMALL_MODEL`, `LLM_LARGE_MODEL`

## Docs

- [architecture.md](docs/architecture.md)
- [rag-pipeline.md](docs/rag-pipeline.md)
- [api.md](docs/api.md)
- [evaluation.md](docs/evaluation.md)
