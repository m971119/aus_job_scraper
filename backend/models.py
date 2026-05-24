from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    seek_url: str = Field(unique=True, index=True)
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
