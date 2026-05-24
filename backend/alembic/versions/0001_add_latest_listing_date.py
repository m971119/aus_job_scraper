"""add latest_listing_date column to job

Revision ID: 0001
Revises:
Create Date: 2026-05-24
"""
import json
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Add column only if it doesn't already exist (safe for DBs created via create_all)
    existing_columns = [c["name"] for c in inspect(conn).get_columns("job")]
    if "latest_listing_date" not in existing_columns:
        with op.batch_alter_table("job") as batch_op:
            batch_op.add_column(sa.Column("latest_listing_date", sa.String(), nullable=True))

    # Backfill: compute max(listed_dates) for any row missing the value
    rows = conn.execute(text("SELECT id, listed_dates FROM job WHERE latest_listing_date IS NULL")).fetchall()
    for row_id, listed_dates_json in rows:
        dates = json.loads(listed_dates_json or "[]")
        if dates:
            conn.execute(
                text("UPDATE job SET latest_listing_date = :d WHERE id = :id"),
                {"d": max(dates), "id": row_id},
            )

    # Create index if missing
    existing_indexes = [i["name"] for i in inspect(conn).get_indexes("job")]
    if "ix_job_latest_listing_date" not in existing_indexes:
        op.create_index("ix_job_latest_listing_date", "job", ["latest_listing_date"])


def downgrade() -> None:
    op.drop_index("ix_job_latest_listing_date", table_name="job")
    with op.batch_alter_table("job") as batch_op:
        batch_op.drop_column("latest_listing_date")
