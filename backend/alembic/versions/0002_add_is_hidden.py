"""add is_hidden column to job

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-24
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_columns = [c["name"] for c in inspect(conn).get_columns("job")]
    if "is_hidden" not in existing_columns:
        with op.batch_alter_table("job") as batch_op:
            batch_op.add_column(
                sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="0")
            )


def downgrade() -> None:
    with op.batch_alter_table("job") as batch_op:
        batch_op.drop_column("is_hidden")
