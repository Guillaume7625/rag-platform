"""add feedback column to messages

Revision ID: 003
Revises: 002_retrieval_trace_metrics
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_feedback"
down_revision = "002_retrieval_trace_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("feedback", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "feedback")
