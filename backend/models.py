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
    seek_urls: str = Field(default="[]")
    title: str
    company: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    suburb: Optional[str] = None
    salary_range: Optional[str] = None
    listed_dates: str = Field(default="[]")
    latest_listing_date: Optional[str] = Field(default=None, index=True)
    is_repost: bool = Field(default=False)
    is_hidden: bool = Field(default=False)
    status: str = Field(default="SAVED")
    notes: Optional[str] = None
    hide_reason: Optional[str] = None
    resume_version_id: Optional[int] = Field(default=None, foreign_key="resume_version.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResumeVersion(SQLModel, table=True):
    __tablename__ = "resume_version"
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    resume_version_id: int = Field(foreign_key="resume_version.id")
    type: str  # "cover_letter" | "advisor"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CoverLetter(SQLModel, table=True):
    __tablename__ = "coverletter"
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", unique=True)
    resume_version_id: int = Field(foreign_key="resume_version.id")
    content: str = Field(default="")
    conversation_id: int = Field(foreign_key="conversation.id")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
