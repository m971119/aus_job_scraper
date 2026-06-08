"""add resume_version table

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-08
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if "resume_version" not in inspect(conn).get_table_names():
        op.create_table(
            "resume_version",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("label", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if "resume_version" in inspect(conn).get_table_names():
        op.drop_table("resume_version")
