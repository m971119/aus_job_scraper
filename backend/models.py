from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)


class JobTag(SQLModel, table=True):
    job_id: int = Field(foreign_key="job.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    seek_url: str = Field(index=True)
    seek_urls: str = Field(default="[]")  # JSON array of all seek paths for this job
    title: str
    company: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    suburb: Optional[str] = None
    salary_range: Optional[str] = None
    listed_dates: str = Field(default="[]")  # JSON array of date strings
    latest_listing_date: Optional[str] = Field(default=None, index=True)
    is_repost: bool = Field(default=False)
    is_hidden: bool = Field(default=False)
    status: str = Field(default="SAVED")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
