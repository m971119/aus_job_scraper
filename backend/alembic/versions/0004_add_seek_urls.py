"""add seek_urls column and drop unique index on seek_url

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {col["name"] for col in inspect(conn).get_columns("job")}

    if "seek_urls" not in columns:
        op.add_column("job", sa.Column("seek_urls", sa.Text(), nullable=False, server_default="'[]'"))
        conn.execute(text("UPDATE job SET seek_urls = json_array(seek_url)"))

    # Drop unique index if it still exists
    indexes = {idx["name"] for idx in inspect(conn).get_indexes("job")}
    if "ix_job_seek_url" in indexes:
        op.drop_index("ix_job_seek_url", table_name="job")


def downgrade() -> None:
    conn = op.get_bind()
    indexes = {idx["name"] for idx in inspect(conn).get_indexes("job")}
    if "ix_job_seek_url" not in indexes:
        op.create_index("ix_job_seek_url", "job", ["seek_url"], unique=True)

    columns = {col["name"] for col in inspect(conn).get_columns("job")}
    if "seek_urls" in columns:
        op.drop_column("job", "seek_urls")
