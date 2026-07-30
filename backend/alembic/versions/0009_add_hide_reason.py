"""add hide_reason to job

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-30
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in inspect(conn).get_columns("job")]
    if "hide_reason" not in cols:
        op.add_column("job", sa.Column("hide_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in inspect(conn).get_columns("job")]
    if "hide_reason" in cols:
        op.drop_column("job", "hide_reason")
