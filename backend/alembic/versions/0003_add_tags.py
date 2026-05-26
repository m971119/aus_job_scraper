"""add tag and job_tag tables with default tags

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

DEFAULT_TAGS = ["Interested", "Laravel", "Python", "AI"]


def upgrade() -> None:
    conn = op.get_bind()
    existing_tables = inspect(conn).get_table_names()

    if "tag" not in existing_tables:
        op.create_table(
            "tag",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False, unique=True),
        )

    if "jobtag" not in existing_tables:
        op.create_table(
            "jobtag",
            sa.Column("job_id", sa.Integer(), sa.ForeignKey("job.id"), primary_key=True),
            sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
        )

    tag_table = sa.table("tag", sa.column("name", sa.String()))
    existing = {row[0] for row in conn.execute(sa.select(tag_table.c.name))}
    to_insert = [{"name": t} for t in DEFAULT_TAGS if t not in existing]
    if to_insert:
        op.bulk_insert(tag_table, to_insert)


def downgrade() -> None:
    op.drop_table("jobtag")
    op.drop_table("tag")
