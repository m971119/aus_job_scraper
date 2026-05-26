from pydantic import BaseModel
from typing import Optional


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

    model_config = {"from_attributes": True}


class JobsPage(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int
