"""add notes column to job

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-03
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {col["name"] for col in inspect(conn).get_columns("job")}
    if "notes" not in columns:
        op.add_column("job", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("job", "notes")
