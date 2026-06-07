"""add status column to job

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-07
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {col["name"] for col in inspect(conn).get_columns("job")}
    if "status" not in columns:
        op.add_column(
            "job",
            sa.Column("status", sa.String(), nullable=False, server_default="SAVED"),
        )


def downgrade() -> None:
    op.drop_column("job", "status")
