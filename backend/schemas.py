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
    max_pages: int = 3


class ScrapeResponse(BaseModel):
    scraped: int
    inserted: int
    updated_reposts: int


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
    is_repost: bool

    model_config = {"from_attributes": True}
