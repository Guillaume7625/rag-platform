# API

Base URL: `http://localhost:8000`

## Auth

```
POST /auth/login          { email, password }       -> { access_token }
GET  /auth/me                                       -> UserOut
```

All other routes require `Authorization: Bearer <token>`.

## Documents

```
POST   /documents/upload          (multipart: file, tags, allowed_roles)
GET    /documents                 -> { items, total }
GET    /documents/{id}            -> DocumentOut
POST   /documents/{id}/reindex
DELETE /documents/{id}
```

## Chat

```
POST /chat/query
{
  "query": "What's the notice period?",
  "conversation_id": null,
  "filters": { "tags": ["contracts"] },
  "force_mode": null
}
```

Response:

```json
{
  "answer": "...",
  "citations": [
    {
      "document_id": "uuid",
      "document_name": "contract.pdf",
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

## Conversations

```
GET /conversations               -> ConversationOut[]
GET /conversations/{id}          -> ConversationDetail
```

## Ops

```
GET /health                      -> { "status": "ok" }
GET /metrics                     -> Prometheus exposition
```
