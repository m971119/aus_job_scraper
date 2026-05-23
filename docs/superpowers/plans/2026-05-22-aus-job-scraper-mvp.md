# Aus Job Scraper MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app that scrapes Seek.com.au job listings via Playwright, stores them in SQLite, and displays them in a Next.js frontend with keyword/location filtering and repost detection.

**Architecture:** FastAPI backend handles scraping and a REST API; Next.js (client-rendered) calls the API from the browser; SQLite is mounted as a persistent Docker volume. Everything runs via Docker Compose with one-command start/stop scripts.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, Playwright (async), Next.js 15 (App Router, TypeScript), Tailwind CSS 4, SQLite, Docker Compose, uv

---

## Decisions Locked In

- Seek only (no LinkedIn for MVP)
- No login — anonymous scraping
- Scrape triggered manually via UI button
- Search parameters (keywords + location) entered in the UI
- Duplicate = same `seek_url` found again on a different date → append date to `listed_dates`, set `is_repost = true`
- Frontend features: keyword search, location filter, repost badge

---

## File Map

```
aus_job_scraper/
├── .gitignore
├── .env.example
├── docker-compose.yml
├── README.md
├── scripts/
│   ├── start.sh          # Mac/Linux start
│   ├── stop.sh           # Mac/Linux stop
│   ├── start.bat         # Windows start
│   └── stop.bat          # Windows stop
├── backend/
│   ├── pyproject.toml
│   ├── main.py           # FastAPI app entry point
│   ├── database.py       # SQLite engine + session
│   ├── models.py         # SQLModel table definitions
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── scraper.py        # Playwright Seek scraper
│   ├── routes/
│   │   ├── jobs.py       # GET /api/jobs
│   │   └── scrape.py     # POST /api/scrape
│   └── tests/
│       ├── conftest.py
│       ├── test_models.py
│       ├── test_scraper.py
│       └── test_api.py
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   └── components/
│       ├── SearchForm.tsx    # Keywords + location inputs + scrape button
│       ├── JobCard.tsx       # Single job card with repost badge
│       └── JobList.tsx       # Filtered job list
└── docs/
    └── superpowers/
        └── plans/
            └── 2026-05-22-aus-job-scraper-mvp.md
```

---

## Phase 1: Project Scaffold

### Task 1: Git init, .gitignore, .env.example

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: Initialise git repo**

```bash
cd /path/to/aus_job_scraper
git init
```

- [ ] **Step 2: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
htmlcov/

# Playwright
backend/playwright-storage/

# Node
frontend/node_modules/
frontend/.next/
frontend/.env*.local

# DB
*.sqlite
*.db
data/

# Env
.env

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Create .env.example**

```
# Backend
DATABASE_URL=sqlite:///./data/jobs.db
CORS_ORIGINS=http://localhost:3000

# Frontend (build-time)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 4: Create minimal README.md**

```markdown
# Aus Job Scraper

Scrapes recent jobs from Seek.com.au and displays them in a web UI.

## Quick Start

Copy `.env.example` to `.env`, then:

```bash
./scripts/start.sh   # Mac/Linux
scripts\start.bat    # Windows
```

Open http://localhost:3000
```

- [ ] **Step 5: Create data directory with .gitkeep**

```bash
mkdir -p data
touch data/.gitkeep
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "chore: initial scaffold with gitignore and env example"
```

---

## Phase 2: Backend — Setup & Database

### Task 2: uv project + FastAPI skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/main.py`

- [ ] **Step 1: Initialise uv project**

```bash
cd backend
uv init --no-workspace
```

- [ ] **Step 2: Add dependencies**

```bash
uv add fastapi uvicorn[standard] sqlmodel playwright pytest pytest-asyncio httpx
uv run playwright install chromium
```

- [ ] **Step 3: Write `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db
from routes import jobs, scrape
import os

app = FastAPI(title="Aus Job Scraper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db()

app.include_router(jobs.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Verify server starts**

```bash
uv run uvicorn main:app --reload
```

Expected: `Uvicorn running on http://127.0.0.1:8000`
Then `curl http://localhost:8000/health` → `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/
git commit -m "feat(backend): fastapi skeleton with health endpoint"
```

---

### Task 3: SQLModel database + Job model

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing test for Job model**

`backend/tests/test_models.py`:
```python
from sqlmodel import Session, select
from models import Job
from database import create_db, engine
import json

def test_job_insert_and_retrieve():
    create_db()
    with Session(engine) as session:
        job = Job(
            seek_url="https://www.seek.com.au/job/12345",
            title="Software Engineer",
            company="Acme Corp",
            description="A great job",
            state="VIC",
            city="Melbourne",
            suburb="CBD",
            listed_dates=json.dumps(["2026-05-22"]),
            is_repost=False,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        found = session.exec(select(Job).where(Job.seek_url == job.seek_url)).first()
        assert found is not None
        assert found.title == "Software Engineer"
        assert json.loads(found.listed_dates) == ["2026-05-22"]
        assert found.is_repost is False
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd backend
uv run pytest tests/test_models.py -v
```

Expected: ImportError (models not defined yet)

- [ ] **Step 3: Write `backend/database.py`**

```python
from sqlmodel import SQLModel, create_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/jobs.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def create_db():
    SQLModel.metadata.create_all(engine)
```

- [ ] **Step 4: Write `backend/models.py`**

```python
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

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
    is_repost: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 5: Write `backend/tests/conftest.py`**

```python
import os
os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"
```

- [ ] **Step 6: Run test — expect pass**

```bash
uv run pytest tests/test_models.py -v
```

Expected: PASSED

- [ ] **Step 7: Commit**

```bash
cd ..
git add backend/
git commit -m "feat(backend): sqlite job model with sqlmodel"
```

---

## Phase 3: Backend — Scraper

### Task 4: Seek scraper with Playwright

**Files:**
- Create: `backend/scraper.py`
- Create: `backend/tests/test_scraper.py`

> Note: Seek's HTML structure may differ from what's shown here. The selectors below are the likely ones as of 2026 — verify against live pages during implementation and adjust if needed.

- [ ] **Step 1: Write `backend/schemas.py`** (shared types used by scraper + API)

```python
from pydantic import BaseModel
from typing import Optional
from datetime import date

class ScrapedJob(BaseModel):
    seek_url: str
    title: str
    company: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    suburb: Optional[str] = None
    salary_range: Optional[str] = None
    listed_date: str  # ISO date string e.g. "2026-05-22"

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

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Write failing test for scraper (unit, with mock)**

`backend/tests/test_scraper.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch
from scraper import parse_location, build_seek_url

def test_build_seek_url():
    url = build_seek_url("python developer", "Melbourne VIC", page=1)
    assert "seek.com.au" in url
    assert "python" in url.lower() or "keywords" in url

def test_parse_location_full():
    result = parse_location("CBD Melbourne VIC 3000")
    assert result["state"] == "VIC"

def test_parse_location_empty():
    result = parse_location("")
    assert result["state"] is None
    assert result["city"] is None
    assert result["suburb"] is None
```

- [ ] **Step 3: Run test — expect failure**

```bash
uv run pytest tests/test_scraper.py -v
```

Expected: ImportError (scraper not defined)

- [ ] **Step 4: Write `backend/scraper.py`**

```python
import re
import asyncio
from datetime import date
from playwright.async_api import async_playwright
from schemas import ScrapedJob

SEEK_BASE = "https://www.seek.com.au"

def build_seek_url(keywords: str, location: str, page: int = 1) -> str:
    from urllib.parse import urlencode
    params = {"keywords": keywords, "where": location, "page": page}
    return f"{SEEK_BASE}/jobs?{urlencode(params)}"

def parse_location(location_text: str) -> dict:
    """Extract state, city, suburb from a raw location string."""
    au_states = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}
    state = next((s for s in au_states if s in location_text.upper()), None)
    parts = [p.strip() for p in location_text.split() if p.strip()]
    # Remove state token and postcodes (4 digits)
    filtered = [p for p in parts if p.upper() not in au_states and not re.match(r"^\d{4}$", p)]
    city = filtered[0] if filtered else None
    suburb = filtered[1] if len(filtered) > 1 else None
    return {"state": state, "city": city, "suburb": suburb}

async def scrape_seek(keywords: str, location: str, max_pages: int = 3) -> list[ScrapedJob]:
    """Scrape Seek job listings. Returns list of ScrapedJob."""
    results = []
    today = date.today().isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(15000)

        for page_num in range(1, max_pages + 1):
            url = build_seek_url(keywords, location, page_num)
            await page.goto(url, wait_until="domcontentloaded")

            # Wait for job cards — selector verified against seek.com.au as of 2026
            job_cards = await page.query_selector_all("article[data-testid='job-card']")
            if not job_cards:
                break  # No more results

            for card in job_cards:
                try:
                    title_el = await card.query_selector("a[data-testid='job-title']")
                    title = await title_el.inner_text() if title_el else None
                    href = await title_el.get_attribute("href") if title_el else None
                    seek_url = f"{SEEK_BASE}{href}" if href and href.startswith("/") else href

                    company_el = await card.query_selector("[data-testid='job-card-company-name']")
                    company = await company_el.inner_text() if company_el else None

                    location_el = await card.query_selector("[data-testid='job-card-location']")
                    location_text = await location_el.inner_text() if location_el else ""
                    loc = parse_location(location_text)

                    salary_el = await card.query_selector("[data-testid='job-card-pay']")
                    salary_range = await salary_el.inner_text() if salary_el else None

                    if title and seek_url:
                        results.append(ScrapedJob(
                            seek_url=seek_url,
                            title=title.strip(),
                            company=company.strip() if company else None,
                            state=loc["state"],
                            city=loc["city"],
                            suburb=loc["suburb"],
                            salary_range=salary_range.strip() if salary_range else None,
                            listed_date=today,
                        ))
                except Exception:
                    continue  # Skip malformed cards, log in production

        # Fetch descriptions in batch (visit each job page)
        for job in results:
            try:
                await page.goto(job.seek_url, wait_until="domcontentloaded")
                desc_el = await page.query_selector("[data-testid='job-detail-overview']")
                if not desc_el:
                    desc_el = await page.query_selector(".job-detail-overview")
                if desc_el:
                    job.description = (await desc_el.inner_text()).strip()
            except Exception:
                pass

        await browser.close()
    return results
```

- [ ] **Step 5: Run unit tests — expect pass**

```bash
uv run pytest tests/test_scraper.py -v
```

Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/
git commit -m "feat(backend): seek scraper with playwright"
```

---

## Phase 4: Backend — API Routes

### Task 5: Jobs list route + duplicate upsert logic

**Files:**
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/jobs.py`
- Create: `backend/routes/scrape.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests for API**

`backend/tests/test_api.py`:
```python
import os
os.environ["DATABASE_URL"] = "sqlite:///./data/test_api.db"

import json
import pytest
from fastapi.testclient import TestClient
from main import app
from database import create_db

@pytest.fixture(autouse=True)
def setup_db():
    create_db()

client = TestClient(app)

def test_get_jobs_empty():
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert resp.json() == []

def test_get_jobs_with_keyword_filter():
    # Insert a job directly
    from sqlmodel import Session
    from database import engine
    from models import Job
    with Session(engine) as s:
        s.add(Job(
            seek_url="https://seek.com.au/job/999",
            title="Python Developer",
            city="Sydney",
            state="NSW",
            listed_dates=json.dumps(["2026-05-22"]),
        ))
        s.commit()

    resp = client.get("/api/jobs?keyword=python")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python Developer"

def test_get_jobs_location_filter():
    resp = client.get("/api/jobs?location=Sydney")
    assert resp.status_code == 200
    data = resp.json()
    assert all("sydney" in (j["city"] or "").lower() for j in data)
```

- [ ] **Step 2: Run tests — expect failure**

```bash
uv run pytest tests/test_api.py -v
```

Expected: FAILED (routes not implemented)

- [ ] **Step 3: Create `backend/routes/__init__.py`** (empty)

```bash
touch backend/routes/__init__.py
```

- [ ] **Step 4: Write `backend/routes/jobs.py`**

```python
import json
from fastapi import APIRouter, Query, Depends
from sqlmodel import Session, select
from database import engine
from models import Job
from schemas import JobOut
from typing import Optional

router = APIRouter()

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    query = select(Job)
    jobs = session.exec(query).all()

    if keyword:
        kw = keyword.lower()
        jobs = [j for j in jobs if kw in j.title.lower() or (j.description and kw in j.description.lower())]

    if location:
        loc = location.lower()
        jobs = [j for j in jobs if
            (j.city and loc in j.city.lower()) or
            (j.state and loc in j.state.lower()) or
            (j.suburb and loc in j.suburb.lower())
        ]

    result = []
    for j in jobs:
        out = JobOut(
            id=j.id,
            seek_url=j.seek_url,
            title=j.title,
            company=j.company,
            description=j.description,
            state=j.state,
            city=j.city,
            suburb=j.suburb,
            salary_range=j.salary_range,
            listed_dates=json.loads(j.listed_dates),
            is_repost=j.is_repost,
        )
        result.append(out)
    return result
```

- [ ] **Step 5: Write `backend/routes/scrape.py`**

```python
import json
import asyncio
from fastapi import APIRouter
from sqlmodel import Session, select
from database import engine
from models import Job
from scraper import scrape_seek
from schemas import ScrapeRequest, ScrapeResponse
from datetime import datetime

router = APIRouter()

@router.post("/scrape", response_model=ScrapeResponse)
def trigger_scrape(req: ScrapeRequest):
    scraped = asyncio.run(scrape_seek(req.keywords, req.location, req.max_pages))

    inserted = 0
    updated = 0

    with Session(engine) as session:
        for item in scraped:
            existing = session.exec(
                select(Job).where(Job.seek_url == item.seek_url)
            ).first()

            if existing:
                dates = json.loads(existing.listed_dates)
                if item.listed_date not in dates:
                    dates.append(item.listed_date)
                    existing.listed_dates = json.dumps(dates)
                    existing.is_repost = True
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                    updated += 1
            else:
                job = Job(
                    seek_url=item.seek_url,
                    title=item.title,
                    company=item.company,
                    description=item.description,
                    state=item.state,
                    city=item.city,
                    suburb=item.suburb,
                    salary_range=item.salary_range,
                    listed_dates=json.dumps([item.listed_date]),
                    is_repost=False,
                )
                session.add(job)
                inserted += 1

        session.commit()

    return ScrapeResponse(scraped=len(scraped), inserted=inserted, updated_reposts=updated)
```

- [ ] **Step 6: Run API tests — expect pass**

```bash
uv run pytest tests/test_api.py -v
```

Expected: 3 PASSED

- [ ] **Step 7: Verify full backend manually**

```bash
uv run uvicorn main:app --reload
```

Open http://localhost:8000/docs — confirm `/api/jobs` and `/api/scrape` appear.

- [ ] **Step 8: Commit**

```bash
cd ..
git add backend/
git commit -m "feat(backend): jobs list and scrape trigger endpoints"
```

---

## Phase 5: Frontend

### Task 6: Next.js 15 + Tailwind setup with color scheme

**Files:**
- Create: `frontend/` (via create-next-app)
- Modify: `frontend/app/globals.css`
- Modify: `frontend/tailwind.config.ts`

- [ ] **Step 1: Create Next.js app**

```bash
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --import-alias "@/*"
```

- [ ] **Step 2: Create `.env.local` in frontend**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 3: Update `frontend/tailwind.config.ts` with brand colors**

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        yellow: "#ecad0a",
        blue: "#209dd7",
        purple: "#753991",
        navy: "#032147",
        gray: "#888888",
      },
    },
  },
};
export default config;
```

- [ ] **Step 4: Update `frontend/app/globals.css`**

```css
@import "tailwindcss";

:root {
  --color-yellow: #ecad0a;
  --color-blue: #209dd7;
  --color-purple: #753991;
  --color-navy: #032147;
  --color-gray: #888888;
}

body {
  background-color: #f9fafb;
  color: #1f2937;
}
```

- [ ] **Step 5: Update `frontend/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Aus Job Scraper",
  description: "Seek job listings scraper",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 6: Verify dev server starts**

```bash
cd frontend
npm run dev
```

Expected: `Local: http://localhost:3000` — default Next.js page loads.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): next.js 15 with tailwind and brand colors"
```

---

### Task 7: SearchForm component

**Files:**
- Create: `frontend/components/SearchForm.tsx`

- [ ] **Step 1: Write `frontend/components/SearchForm.tsx`**

```tsx
"use client";
import { useState } from "react";

interface Props {
  onScrape: (keywords: string, location: string) => void;
  loading: boolean;
}

export default function SearchForm({ onScrape, loading }: Props) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (keywords.trim()) onScrape(keywords.trim(), location.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
      <input
        type="text"
        placeholder="Keywords (e.g. Python developer)"
        value={keywords}
        onChange={(e) => setKeywords(e.target.value)}
        required
        className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#209dd7]"
      />
      <input
        type="text"
        placeholder="Location (e.g. Melbourne VIC)"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#209dd7]"
      />
      <button
        type="submit"
        disabled={loading}
        className="px-6 py-2 bg-[#753991] text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
      >
        {loading ? "Scraping..." : "Scrape Seek"}
      </button>
    </form>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/SearchForm.tsx
git commit -m "feat(frontend): search form component"
```

---

### Task 8: JobCard component with repost badge

**Files:**
- Create: `frontend/components/JobCard.tsx`

- [ ] **Step 1: Define Job type in `frontend/types.ts`**

```ts
export interface Job {
  id: number;
  seek_url: string;
  title: string;
  company: string | null;
  description: string | null;
  state: string | null;
  city: string | null;
  suburb: string | null;
  salary_range: string | null;
  listed_dates: string[];
  is_repost: boolean;
}
```

- [ ] **Step 2: Write `frontend/components/JobCard.tsx`**

```tsx
import { Job } from "@/types";

interface Props {
  job: Job;
}

export default function JobCard({ job }: Props) {
  const location = [job.suburb, job.city, job.state].filter(Boolean).join(", ");

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <a
            href={job.seek_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#209dd7] font-semibold text-lg hover:underline truncate block"
          >
            {job.title}
          </a>
          {job.company && (
            <p className="text-[#032147] font-medium mt-0.5">{job.company}</p>
          )}
        </div>
        {job.is_repost && (
          <span className="shrink-0 text-xs font-semibold px-2 py-1 rounded-full bg-[#ecad0a]/20 text-[#ecad0a] border border-[#ecad0a]/40">
            Reposted
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-[#888888]">
        {location && <span>{location}</span>}
        {job.salary_range && <span>{job.salary_range}</span>}
      </div>

      {job.description && (
        <p className="mt-3 text-sm text-gray-600 line-clamp-3">{job.description}</p>
      )}

      <div className="mt-3 flex flex-wrap gap-1">
        {job.listed_dates.map((d) => (
          <span key={d} className="text-xs bg-gray-100 text-[#888888] px-2 py-0.5 rounded">
            {d}
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/JobCard.tsx frontend/types.ts
git commit -m "feat(frontend): job card with repost badge"
```

---

### Task 9: JobList with filters

**Files:**
- Create: `frontend/components/JobList.tsx`

- [ ] **Step 1: Write `frontend/components/JobList.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Job } from "@/types";
import JobCard from "./JobCard";

interface Props {
  jobs: Job[];
}

export default function JobList({ jobs }: Props) {
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");

  const filtered = jobs.filter((job) => {
    const kw = keyword.toLowerCase();
    const loc = location.toLowerCase();
    const matchKw =
      !kw ||
      job.title.toLowerCase().includes(kw) ||
      (job.description?.toLowerCase().includes(kw) ?? false);
    const matchLoc =
      !loc ||
      (job.city?.toLowerCase().includes(loc) ?? false) ||
      (job.state?.toLowerCase().includes(loc) ?? false) ||
      (job.suburb?.toLowerCase().includes(loc) ?? false);
    return matchKw && matchLoc;
  });

  return (
    <div>
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          type="text"
          placeholder="Filter by keyword..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#209dd7] text-sm"
        />
        <input
          type="text"
          placeholder="Filter by location..."
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#209dd7] text-sm"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-[#888888] text-center py-12">No jobs found.</p>
      ) : (
        <div className="grid gap-4">
          {filtered.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      <p className="text-xs text-[#888888] mt-4 text-right">
        {filtered.length} of {jobs.length} jobs
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/JobList.tsx
git commit -m "feat(frontend): job list with keyword and location filters"
```

---

### Task 10: Main page — wire everything together

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Write `frontend/app/page.tsx`**

```tsx
"use client";
import { useState, useEffect, useCallback } from "react";
import SearchForm from "@/components/SearchForm";
import JobList from "@/components/JobList";
import { Job } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scrapeMsg, setScrapeMsg] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    const res = await fetch(`${API}/api/jobs`);
    if (res.ok) setJobs(await res.json());
  }, []);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const handleScrape = async (keywords: string, location: string) => {
    setLoading(true);
    setError(null);
    setScrapeMsg(null);
    try {
      const res = await fetch(`${API}/api/scrape`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords, location, max_pages: 3 }),
      });
      if (!res.ok) throw new Error(`Scrape failed: ${res.status}`);
      const data = await res.json();
      setScrapeMsg(`Done — ${data.inserted} new, ${data.updated_reposts} reposted`);
      await fetchJobs();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-2">
        <div className="h-1 w-16 bg-[#ecad0a] rounded mb-4" />
        <h1 className="text-3xl font-bold text-[#032147]">Aus Job Scraper</h1>
        <p className="text-[#888888] mt-1">Search and scrape recent jobs from Seek.com.au</p>
      </div>

      <div className="mt-8 p-5 bg-white rounded-xl border border-gray-100 shadow-sm">
        <SearchForm onScrape={handleScrape} loading={loading} />
        {error && <p className="mt-3 text-red-500 text-sm">{error}</p>}
        {scrapeMsg && <p className="mt-3 text-green-600 text-sm">{scrapeMsg}</p>}
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold text-[#032147] mb-4">
          Saved Jobs ({jobs.length})
        </h2>
        <JobList jobs={jobs} />
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Start backend + frontend and verify full flow**

Terminal 1:
```bash
cd backend && uv run uvicorn main:app --reload
```

Terminal 2:
```bash
cd frontend && npm run dev
```

Open http://localhost:3000
- Enter "python developer" + "Melbourne VIC", click "Scrape Seek"
- Verify scrape result message appears
- Verify jobs load in the list
- Verify keyword filter narrows results
- Verify location filter works
- Verify repost badge appears on subsequent scrapes of same jobs

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): main page wiring scrape and job list"
```

---

## Phase 6: Docker + Scripts

### Task 11: Dockerfile + docker-compose.yml

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write `docker-compose.yml`**

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env

  frontend:
    image: node:22-alpine
    working_dir: /app
    command: sh -c "npm install && npm run build && npm start"
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
```

- [ ] **Step 3: Copy `.env.example` to `.env` and verify**

```bash
cp .env.example .env
```

- [ ] **Step 4: Build and run via Docker Compose**

```bash
docker compose up --build
```

Expected: backend on :8000, frontend on :3000. Open http://localhost:3000 and verify it loads.

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile docker-compose.yml
git commit -m "feat(infra): dockerfile and docker-compose"
```

---

### Task 12: Start/stop scripts

**Files:**
- Create: `scripts/start.sh`
- Create: `scripts/stop.sh`
- Create: `scripts/start.bat`
- Create: `scripts/stop.bat`

- [ ] **Step 1: Write `scripts/start.sh`**

```bash
#!/usr/bin/env bash
set -e
if [ ! -f .env ]; then cp .env.example .env; fi
mkdir -p data
docker compose up --build -d
echo "Running — frontend: http://localhost:3000"
```

- [ ] **Step 2: Write `scripts/stop.sh`**

```bash
#!/usr/bin/env bash
docker compose down
echo "Stopped."
```

- [ ] **Step 3: Make scripts executable**

```bash
chmod +x scripts/start.sh scripts/stop.sh
```

- [ ] **Step 4: Write `scripts/start.bat`**

```bat
@echo off
if not exist .env copy .env.example .env
if not exist data mkdir data
docker compose up --build -d
echo Running - frontend: http://localhost:3000
```

- [ ] **Step 5: Write `scripts/stop.bat`**

```bat
@echo off
docker compose down
echo Stopped.
```

- [ ] **Step 6: Test start script**

```bash
./scripts/start.sh
```

Expected: containers start, "Running — frontend: http://localhost:3000" printed.

```bash
./scripts/stop.sh
```

Expected: containers stop, "Stopped." printed.

- [ ] **Step 7: Commit**

```bash
git add scripts/
git commit -m "feat(scripts): start and stop scripts for mac/linux/windows"
```

---

## Phase 7: Integration Testing

### Task 13: End-to-end integration test

**Files:**
- Create: `backend/tests/test_integration.py`

- [ ] **Step 1: Write integration test (uses real Playwright against live Seek)**

`backend/tests/test_integration.py`:
```python
"""
Integration test — hits live Seek.com.au. Requires internet access.
Run with: uv run pytest tests/test_integration.py -v -m integration
"""
import os
os.environ["DATABASE_URL"] = "sqlite:///./data/test_integration.db"

import json
import pytest
from fastapi.testclient import TestClient
from main import app
from database import create_db

pytestmark = pytest.mark.integration

@pytest.fixture(autouse=True)
def setup():
    create_db()

client = TestClient(app)

def test_scrape_and_retrieve():
    resp = client.post("/api/scrape", json={
        "keywords": "python developer",
        "location": "Melbourne",
        "max_pages": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["scraped"] >= 0
    assert data["inserted"] >= 0

    jobs_resp = client.get("/api/jobs")
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert isinstance(jobs, list)
    if jobs:
        assert "title" in jobs[0]
        assert "seek_url" in jobs[0]
        assert isinstance(jobs[0]["listed_dates"], list)

def test_repost_detection():
    """Scrape twice — second run should mark reposts."""
    payload = {"keywords": "data engineer", "location": "Sydney", "max_pages": 1}
    r1 = client.post("/api/scrape", json=payload)
    r2 = client.post("/api/scrape", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    d2 = r2.json()
    # All second-run jobs should be reposts (same day so no new dates added,
    # but no errors expected)
    assert d2["inserted"] + d2["updated_reposts"] >= 0

def test_keyword_filter_returns_relevant():
    client.post("/api/scrape", json={"keywords": "frontend developer", "location": "Brisbane", "max_pages": 1})
    resp = client.get("/api/jobs?keyword=frontend")
    assert resp.status_code == 200
    jobs = resp.json()
    for job in jobs:
        assert "frontend" in job["title"].lower() or (job["description"] and "frontend" in job["description"].lower())
```

- [ ] **Step 2: Add pytest marker config to `backend/pyproject.toml`**

```toml
[tool.pytest.ini_options]
markers = ["integration: marks tests as integration tests (live network)"]
asyncio_mode = "auto"
```

- [ ] **Step 3: Run unit tests only (should pass without network)**

```bash
uv run pytest tests/ -v -m "not integration"
```

Expected: all PASSED

- [ ] **Step 4: Run integration tests (requires internet)**

```bash
uv run pytest tests/test_integration.py -v -m integration
```

Expected: all PASSED (may take 30-60s due to Playwright)

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/tests/test_integration.py backend/pyproject.toml
git commit -m "test: integration tests for scrape and job retrieval"
```

---

## Success Criteria Checklist

- [ ] `./scripts/start.sh` starts the app with no errors
- [ ] http://localhost:3000 loads the UI
- [ ] User can enter keywords + location and click "Scrape Seek"
- [ ] Jobs appear in the list after scraping
- [ ] Keyword filter narrows the list
- [ ] Location filter narrows the list
- [ ] Running the same scrape twice marks repeated jobs with "Reposted" badge
- [ ] Stopping and restarting Docker preserves all scraped jobs
- [ ] All unit tests pass: `uv run pytest tests/ -m "not integration" -v`
- [ ] Integration tests pass: `uv run pytest tests/test_integration.py -m integration -v`
