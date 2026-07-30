from pydantic import BaseModel, field_validator
from typing import Literal, Optional
from datetime import datetime


class TagOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()


class NotesUpdate(BaseModel):
    notes: Optional[str] = None


JobStatus = Literal["SAVED", "APPLIED", "INTERVIEWING", "OFFER", "ACCEPTED", "REJECTED", "WITHDRAWN", "GHOSTED"]


class StatusUpdate(BaseModel):
    status: JobStatus


class ScrapedJob(BaseModel):
    seek_url: str
    title: str
    company: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    suburb: Optional[str] = None
    salary_range: Optional[str] = None
    listed_date: str  # ISO date string e.g. "2026-05-23"


class ScrapeRequest(BaseModel):
    keywords: str
    location: str


class ScrapeResponse(BaseModel):
    scraped: int
    inserted: int
    updated_reposts: int
    skipped_hidden: int


class ScrapeStatus(BaseModel):
    status: str           # "idle" | "running" | "done" | "cancelled" | "error"
    phase: str = "seeking"  # "seeking" | "comparing"
    current_page: int = 0
    jobs_scraped: int = 0
    jobs_compared: int = 0
    inserted: int = 0
    updated_reposts: int = 0
    skipped_hidden: int = 0
    error: str | None = None


class JobOut(BaseModel):
    id: int
    seek_url: str
    seek_urls: list[str] = []
    title: str
    company: Optional[str]
    description: Optional[str]
    state: Optional[str]
    city: Optional[str]
    suburb: Optional[str]
    salary_range: Optional[str]
    listed_dates: list[str]
    latest_listing_date: Optional[str]
    is_repost: bool
    is_hidden: bool
    notes: Optional[str] = None
    hide_reason: Optional[str] = None
    status: str = "SAVED"
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}


class JobsPage(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int


class ResumeVersionMeta(BaseModel):
    id: int
    label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeVersionOut(BaseModel):
    id: int
    label: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeVersionCreate(BaseModel):
    label: str
    content: str

    @field_validator("label")
    @classmethod
    def label_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("label must not be empty")
        return v.strip()


class ResumeVersionLink(BaseModel):
    resume_version_id: Optional[int] = None


class GenerateRequest(BaseModel):
    model: str


class ChatRequest(BaseModel):
    message: str
    model: str


class CoverLetterUpdate(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CoverLetterOut(BaseModel):
    id: int
    job_id: int
    resume_version_id: int
    content: str
    conversation_id: int
    messages: list[MessageOut] = []
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdvisorOut(BaseModel):
    conversation_id: int
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}


class ModelInfo(BaseModel):
    id: str
    label: str
