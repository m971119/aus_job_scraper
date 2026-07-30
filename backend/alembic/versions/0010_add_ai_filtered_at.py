"""add ai_filtered_at to job

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-30
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in inspect(conn).get_columns("job")]
    if "ai_filtered_at" not in cols:
        op.add_column("job", sa.Column("ai_filtered_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in inspect(conn).get_columns("job")]
    if "ai_filtered_at" in cols:
        op.drop_column("job", "ai_filtered_at")
