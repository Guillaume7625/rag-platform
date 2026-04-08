# Evaluation

The platform stores `evaluation_runs` and `evaluation_cases` in Postgres so
you can:

1. Define a curated test set per tenant.
2. Replay the test set on every deploy.
3. Compare runs over time (mean lexical score, citation hit-rate, etc.).

## Replacing the lexical scorer

`EvaluationService.score_lexical` is a stub. Real options:

- **RAGAS** (faithfulness, answer_relevancy, context_precision/recall)
- **LLM-as-judge** with a strong model
- **Citation overlap**: did the cited chunks come from the expected docs?

## Suggested metrics

- `retrieval_recall@k` against gold chunks
- `citation_precision` (cited chunks ⊆ gold chunks)
- `answer_score` (RAGAS or judge)
- `mode_distribution` (standard vs deep)
- `latency_ms` p50 / p95
