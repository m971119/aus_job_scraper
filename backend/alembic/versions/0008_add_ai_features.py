"""add ai features: resume_version_id on job, conversation, message, cover_letter tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    tables = inspect(conn).get_table_names()

    if "resume_version_id" not in [c["name"] for c in inspect(conn).get_columns("job")]:
        op.add_column("job", sa.Column("resume_version_id", sa.Integer(), nullable=True))

    if "conversation" not in tables:
        op.create_table(
            "conversation",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), sa.ForeignKey("job.id"), nullable=False),
            sa.Column("resume_version_id", sa.Integer(), sa.ForeignKey("resume_version.id"), nullable=False),
            sa.Column("type", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_conversation_job_id", "conversation", ["job_id"])

    if "message" not in tables:
        op.create_table(
            "message",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversation.id"), nullable=False),
            sa.Column("role", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_message_conversation_id", "message", ["conversation_id"])

    if "coverletter" not in tables:
        op.create_table(
            "coverletter",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), sa.ForeignKey("job.id"), nullable=False),
            sa.Column("resume_version_id", sa.Integer(), sa.ForeignKey("resume_version.id"), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversation.id"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_id"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    tables = inspect(conn).get_table_names()
    if "coverletter" in tables:
        op.drop_table("coverletter")
    if "message" in tables:
        op.drop_index("ix_message_conversation_id", "message")
        op.drop_table("message")
    if "conversation" in tables:
        op.drop_index("ix_conversation_job_id", "conversation")
        op.drop_table("conversation")
    cols = [c["name"] for c in inspect(conn).get_columns("job")]
    if "resume_version_id" in cols:
        op.drop_column("job", "resume_version_id")
