# RAG Pipeline

## Parameters

| Parameter           | Default | Notes                                  |
|---------------------|---------|----------------------------------------|
| Child chunk tokens  | 220     | Range 180–260                          |
| Child overlap       | 40      | Tokens                                 |
| Parent chunk tokens | 1000    | Range 800–1100                         |
| Retrieval top-k     | 50      | Hybrid dense + sparse                  |
| Rerank top-k        | 20      | Cross-encoder rerank                   |
| Context top-k       | 6       | Final parent contexts sent to the LLM  |

## Routing rules

- `standard` for factual / one-intent / well-scored queries
- `deep` triggered by:
  - keywords: compare, différence, vs, synthèse, all the…
  - multiple `?`
  - very long query (>40 tokens)
  - low retrieval scores or large variance

## ACL filters

Every Qdrant point payload includes:

```
{
  "chunk_id": "...",
  "parent_id": "...",
  "document_id": "...",
  "document_version_id": "...",
  "tenant_id": "...",
  "page": 12,
  "section_title": "...",
  "tags": ["finance", "policy"],
  "source_name": "contract.pdf",
  "allowed_roles": ["member", "admin"],
  "content": "..."
}
```

Filters are applied **before** the dense and sparse prefetches inside the
hybrid query, so a low-privilege user can never see chunks they're not
allowed to read.

## Confidence score

A simple heuristic: `clip(top_rerank_score / 2.0, 0, 1)`. Replace with a
calibrated model in production.
