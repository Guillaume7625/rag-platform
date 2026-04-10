"""add latency and cache columns to retrieval_traces

Revision ID: 002_retrieval_trace_metrics
Revises: 001_initial
Create Date: 2026-04-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_retrieval_trace_metrics"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("retrieval_traces", sa.Column("embed_ms", sa.Integer(), nullable=True))
    op.add_column("retrieval_traces", sa.Column("search_ms", sa.Integer(), nullable=True))
    op.add_column("retrieval_traces", sa.Column("rerank_ms", sa.Integer(), nullable=True))
    op.add_column("retrieval_traces", sa.Column("generate_ms", sa.Integer(), nullable=True))
    op.add_column("retrieval_traces", sa.Column("embed_cache_hit", sa.Boolean(), nullable=True))
    op.add_column("retrieval_traces", sa.Column("rerank_cache_hit", sa.Boolean(), nullable=True))
    op.add_column("retrieval_traces", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column(
        "retrieval_traces",
        sa.Column("expansion_queries", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("retrieval_traces", "expansion_queries")
    op.drop_column("retrieval_traces", "confidence")
    op.drop_column("retrieval_traces", "rerank_cache_hit")
    op.drop_column("retrieval_traces", "embed_cache_hit")
    op.drop_column("retrieval_traces", "generate_ms")
    op.drop_column("retrieval_traces", "rerank_ms")
    op.drop_column("retrieval_traces", "search_ms")
    op.drop_column("retrieval_traces", "embed_ms")
