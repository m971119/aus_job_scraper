# Job Application Status Column Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `status` enum column to jobs to track the application pipeline, show it as a badge on job cards, make it editable in the detail view, and add a new Applications page filtered to non-SAVED jobs with a tab bar.

**Architecture:** Backend adds a `status` string field (default `"SAVED"`) to the Job model with a new Alembic migration and a PATCH endpoint + filter query params. Frontend adds a `StatusBadge` component with 8 distinct colors, wires it into `JobCard` and the detail page, and introduces a new `/applications` page with a horizontal tab bar. A top nav bar is added to `layout.tsx` for navigation between the two pages.

**Tech Stack:** FastAPI, SQLModel, Alembic, SQLite (backend); Next.js 14 App Router, TypeScript, Tailwind CSS v4 (frontend); pytest + FastAPI TestClient (tests).

---

## File Structure

### New Files
- `backend/alembic/versions/0006_add_status.py` — Alembic migration, adds `status` column
- `backend/tests/test_status.py` — tests for status field, PATCH endpoint, filter params
- `frontend/components/StatusBadge.tsx` — status badge + exported constants
- `frontend/components/Nav.tsx` — top nav bar (client component, uses `usePathname`)
- `frontend/app/applications/page.tsx` — Applications page with tab bar

### Modified Files
- `backend/models.py` — add `status: str` field to `Job`
- `backend/schemas.py` — add `StatusUpdate` schema; add `status` to `JobOut`
- `backend/routes/jobs.py` — add `status` + `not_saved` query params to `list_jobs`; add PATCH `/jobs/{id}/status`; update `_to_out` to include `status`
- `frontend/types.ts` — add `JobStatus` type; add `status` to `Job` interface
- `frontend/components/JobCard.tsx` — render `<StatusBadge>` in card header
- `frontend/app/jobs/[id]/page.tsx` — add status state + dropdown editor
- `frontend/app/layout.tsx` — import and render `<Nav>`

---

## Task 1: DB Migration

**Files:**
- Create: `backend/alembic/versions/0006_add_status.py`

- [ ] **Step 1: Write the migration**

```python
"""add status column to job

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-07
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {col["name"] for col in inspect(conn).get_columns("job")}
    if "status" not in columns:
        op.add_column(
            "job",
            sa.Column("status", sa.String(), nullable=False, server_default="SAVED"),
        )


def downgrade() -> None:
    op.drop_column("job", "status")
```

- [ ] **Step 2: Run the migration**

Run from `backend/`:
```bash
uv run alembic upgrade head
```
Expected: `Running upgrade 0005 -> 0006, add status column to job`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/0006_add_status.py
git commit -m "feat(db): add status column to job table"
```

---

## Task 2: Backend — Model, Schemas, Routes, Tests

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/schemas.py`
- Modify: `backend/routes/jobs.py`
- Create: `backend/tests/test_status.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_status.py`:

```python
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_status.db")

import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import engine
from models import Job


@pytest.fixture(autouse=True)
def clean_db():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


client = TestClient(app)


def make_job(**kwargs) -> Job:
    defaults = dict(
        seek_url="https://seek.com.au/job/1",
        title="Dev",
        listed_dates=json.dumps(["2026-05-24"]),
        latest_listing_date="2026-05-24",
    )
    return Job(**{**defaults, **kwargs})


def test_job_status_defaults_to_saved():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "SAVED"


def test_update_status():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    resp = client.patch(f"/api/jobs/{job_id}/status", json={"status": "APPLIED"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPLIED"


def test_update_status_not_found():
    resp = client.patch("/api/jobs/99999/status", json={"status": "APPLIED"})
    assert resp.status_code == 404


def test_status_returned_in_job_list():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        j.status = "INTERVIEWING"
        s.add(j)
        s.commit()

    resp = client.get("/api/jobs")
    assert resp.json()["items"][0]["status"] == "INTERVIEWING"


def test_filter_by_exact_status():
    with Session(engine) as s:
        j1 = make_job(seek_url="https://seek.com.au/job/1", title="Applied Job")
        j1.status = "APPLIED"
        j2 = make_job(seek_url="https://seek.com.au/job/2", title="Saved Job")
        j2.status = "SAVED"
        s.add(j1)
        s.add(j2)
        s.commit()

    resp = client.get("/api/jobs?status=APPLIED")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Applied Job"


def test_filter_not_saved_excludes_saved_jobs():
    with Session(engine) as s:
        j1 = make_job(seek_url="https://seek.com.au/job/1", title="Applied Job")
        j1.status = "APPLIED"
        j2 = make_job(seek_url="https://seek.com.au/job/2", title="Saved Job")
        j2.status = "SAVED"
        j3 = make_job(seek_url="https://seek.com.au/job/3", title="Rejected Job")
        j3.status = "REJECTED"
        s.add(j1)
        s.add(j2)
        s.add(j3)
        s.commit()

    resp = client.get("/api/jobs?not_saved=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    titles = [j["title"] for j in data["items"]]
    assert "Saved Job" not in titles
    assert "Applied Job" in titles
    assert "Rejected Job" in titles
```

- [ ] **Step 2: Run tests to confirm they fail**

Run from `backend/`:
```bash
uv run pytest tests/test_status.py -v
```
Expected: Multiple failures — `KeyError: 'status'` or `AssertionError` because `status` field doesn't exist yet.

- [ ] **Step 3: Update `backend/models.py` — add status field**

Add `status` after `is_hidden` on line 31:

```python
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Update `backend/schemas.py` — add `StatusUpdate` and `status` to `JobOut`**

Add `StatusUpdate` after `NotesUpdate` (after line 24):
```python
class StatusUpdate(BaseModel):
    status: str
```

Add `status: str = "SAVED"` to `JobOut` after `notes` (line 78):
```python
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
    status: str = "SAVED"
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Update `backend/routes/jobs.py`**

**5a.** Update the import line to add `StatusUpdate`:
```python
from schemas import JobOut, JobsPage, NotesUpdate, StatusUpdate, TagOut
```

**5b.** Add `status` and `not_saved` query params to `list_jobs` (after the `visibility` param on line 27):
```python
@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    include_tag: Optional[str] = Query(None),
    exclude_tag: Optional[str] = Query(None),
    is_repost: Literal["all", "originals", "reposts"] = Query("all"),
    visibility: Literal["visible", "hidden", "all"] = Query("visible"),
    status: Optional[str] = Query(None),
    not_saved: bool = Query(False),
    sort: Literal["latest", "oldest"] = Query("latest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
):
```

**5c.** Add status filter logic after the `is_repost` filter block (after line 77):
```python
    if not_saved:
        query = query.where(Job.status != "SAVED")
    elif status:
        query = query.where(Job.status == status)
```

**5d.** Add PATCH status endpoint after `update_notes` (after line 128):
```python
@router.patch("/jobs/{job_id}/status", response_model=JobOut)
def update_status(job_id: int, body: StatusUpdate, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = body.status
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)
```

**5e.** Update `_to_out` to include `status` (after `is_hidden=j.is_hidden,`):
```python
def _to_out(j: Job, session: Session) -> JobOut:
    return JobOut(
        id=j.id,
        seek_url=f"{SEEK_BASE}{j.seek_url}",
        seek_urls=[f"{SEEK_BASE}{p}" for p in json.loads(j.seek_urls or "[]")],
        title=j.title,
        company=j.company,
        description=j.description,
        state=j.state,
        city=j.city,
        suburb=j.suburb,
        salary_range=j.salary_range,
        listed_dates=json.loads(j.listed_dates),
        latest_listing_date=j.latest_listing_date,
        is_repost=j.is_repost,
        is_hidden=j.is_hidden,
        status=j.status,
        notes=j.notes,
        tags=_get_job_tags(session, j.id),
    )
```

- [ ] **Step 6: Run tests to confirm they pass**

Run from `backend/`:
```bash
uv run pytest tests/test_status.py -v
```
Expected: All 6 tests pass.

Also run the full suite to check no regressions:
```bash
uv run pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/models.py backend/schemas.py backend/routes/jobs.py backend/tests/test_status.py
git commit -m "feat(api): add status field and filter/update endpoints"
```

---

## Task 3: Frontend — Types and StatusBadge Component

**Files:**
- Modify: `frontend/types.ts`
- Create: `frontend/components/StatusBadge.tsx`

- [ ] **Step 1: Update `frontend/types.ts`**

Replace the entire file with:
```typescript
export type JobStatus =
  | "SAVED"
  | "APPLIED"
  | "INTERVIEWING"
  | "OFFER"
  | "ACCEPTED"
  | "REJECTED"
  | "WITHDRAWN"
  | "GHOSTED";

export interface Tag {
  id: number;
  name: string;
}

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
  latest_listing_date: string | null;
  is_repost: boolean;
  is_hidden: boolean;
  status: JobStatus;
  notes: string | null;
  tags: Tag[];
}

export interface JobsPage {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface ScrapeStatus {
  status: string;
  phase: string;
  current_page: number;
  jobs_scraped: number;
  jobs_compared: number;
  inserted: number;
  updated_reposts: number;
  skipped_hidden: number;
  error: string | null;
}
```

- [ ] **Step 2: Create `frontend/components/StatusBadge.tsx`**

```tsx
import { JobStatus } from "@/types";

export const JOB_STATUSES: JobStatus[] = [
  "SAVED",
  "APPLIED",
  "INTERVIEWING",
  "OFFER",
  "ACCEPTED",
  "REJECTED",
  "WITHDRAWN",
  "GHOSTED",
];

export const STATUS_LABELS: Record<JobStatus, string> = {
  SAVED: "Saved",
  APPLIED: "Applied",
  INTERVIEWING: "Interviewing",
  OFFER: "Offer",
  ACCEPTED: "Accepted",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
  GHOSTED: "Ghosted",
};

const STATUS_STYLES: Record<JobStatus, string> = {
  SAVED: "bg-gray-100 text-gray-500 border-gray-300",
  APPLIED: "bg-primary/10 text-primary border-primary/30",
  INTERVIEWING: "bg-accent/20 text-amber-700 border-accent/40",
  OFFER: "bg-green-100 text-green-700 border-green-300",
  ACCEPTED: "bg-green-200 text-green-800 border-green-400",
  REJECTED: "bg-red-100 text-red-600 border-red-300",
  WITHDRAWN: "bg-slate-100 text-slate-500 border-slate-300",
  GHOSTED: "bg-secondary/10 text-secondary border-secondary/30",
};

export default function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`text-xs font-semibold px-2 py-1 rounded-full border ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/types.ts frontend/components/StatusBadge.tsx
git commit -m "feat(frontend): add JobStatus type and StatusBadge component"
```

---

## Task 4: Status Badge on JobCard

**Files:**
- Modify: `frontend/components/JobCard.tsx`

- [ ] **Step 1: Update `frontend/components/JobCard.tsx`**

Add the import at the top (after the `SponsorLookup` import):
```tsx
import StatusBadge from "./StatusBadge";
```

Replace the header row (lines 37–58) to add the status badge alongside the repost badge:

```tsx
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <Link
            href={`/jobs/${job.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary font-semibold text-lg hover:underline truncate block"
          >
            {job.title}
          </Link>
          {job.company && (
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-navy font-medium">{job.company}</p>
              <SponsorLookup companyName={job.company} sponsors={sponsors} />
            </div>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <StatusBadge status={job.status} />
          {job.is_repost && (
            <span className="text-xs font-semibold px-2 py-1 rounded-full bg-accent/20 text-accent border border-accent/40">
              Reposted
            </span>
          )}
        </div>
      </div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/JobCard.tsx
git commit -m "feat(frontend): show status badge on job cards"
```

---

## Task 5: Status Editor in Job Detail Page

**Files:**
- Modify: `frontend/app/jobs/[id]/page.tsx`

- [ ] **Step 1: Update `frontend/app/jobs/[id]/page.tsx`**

Add imports at the top (after existing imports):
```tsx
import StatusBadge, { JOB_STATUSES, STATUS_LABELS } from "@/components/StatusBadge";
import { JobStatus } from "@/types";
```

Add `status` state after the existing state declarations (after line 32):
```tsx
  const [status, setStatus] = useState<JobStatus>("SAVED");
```

Add a `useEffect` to sync status when job loads (after the existing sponsors useEffect):
```tsx
  useEffect(() => {
    if (job) setStatus(job.status);
  }, [job]);
```

Add the status change handler (after `handleUnhide`):
```tsx
  const handleStatusChange = async (newStatus: JobStatus) => {
    setStatus(newStatus);
    await fetch(`${API}/api/jobs/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
  };
```

In the JSX, replace the header section (the `flex items-start justify-between` div, lines 83–108) to add a status row below company:

```tsx
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="h-1 w-12 bg-accent rounded mb-3" />
            <h1 className="text-2xl font-bold text-navy">
              <a
                href={job.seek_url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary transition-colors"
              >
                {job.title}
              </a>
            </h1>
            {job.company && (
              <div className="flex items-center gap-2 mt-1">
                <p className="text-primary font-medium">{job.company}</p>
                <SponsorLookup companyName={job.company} sponsors={sponsors} />
              </div>
            )}
            <div className="mt-2 flex items-center gap-2">
              <span className="text-xs text-muted font-medium">Status</span>
              <select
                value={status}
                onChange={(e) => handleStatusChange(e.target.value as JobStatus)}
                className="text-xs border border-gray-200 rounded-lg px-2 py-1 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {JOB_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {job.is_repost && (
            <span className="shrink-0 text-xs font-semibold px-2 py-1 rounded-full bg-accent/20 text-accent border border-accent/40">
              Reposted
            </span>
          )}
        </div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/jobs/[id]/page.tsx
git commit -m "feat(frontend): add status dropdown editor in job detail"
```

---

## Task 6: Applications Page

**Files:**
- Create: `frontend/app/applications/page.tsx`

- [ ] **Step 1: Create `frontend/app/applications/page.tsx`**

```tsx
"use client";
import { useState, useEffect, useCallback } from "react";
import { JobsPage, Tag, JobStatus } from "@/types";
import JobCard from "@/components/JobCard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PAGE_SIZE = 25;

type Tab = "ALL" | JobStatus;

const TABS: { value: Tab; label: string }[] = [
  { value: "ALL", label: "All Applied" },
  { value: "APPLIED", label: "Applied" },
  { value: "INTERVIEWING", label: "Interviewing" },
  { value: "OFFER", label: "Offer" },
  { value: "ACCEPTED", label: "Accepted" },
  { value: "REJECTED", label: "Rejected" },
  { value: "WITHDRAWN", label: "Withdrawn" },
  { value: "GHOSTED", label: "Ghosted" },
];

export default function ApplicationsPage() {
  const [tab, setTab] = useState<Tab>("APPLIED");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<JobsPage>({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [sponsors, setSponsors] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API}/api/tags`).then((r) => r.json()).then(setAllTags);
    fetch(`${API}/api/sponsors`).then((r) => r.json()).then((d) => setSponsors(d.sponsors));
  }, []);

  useEffect(() => {
    setPage(1);
  }, [tab]);

  const buildParams = useCallback(
    (p: number) => {
      const params = new URLSearchParams({
        visibility: "visible",
        sort: "latest",
        page: String(p),
        page_size: String(PAGE_SIZE),
      });
      if (tab === "ALL") {
        params.set("not_saved", "true");
      } else {
        params.set("status", tab);
      }
      return params;
    },
    [tab]
  );

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/jobs?${buildParams(page)}`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) setData(d);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [page, buildParams]);

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  const handleHide = async (id: number) => {
    setData((prev) => ({
      ...prev,
      items: prev.items.filter((j) => j.id !== id),
      total: prev.total - 1,
    }));
    await fetch(`${API}/api/jobs/${id}/hide`, { method: "PATCH" });
  };

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-navy mb-6">Applications</h1>

      <div className="flex gap-0.5 overflow-x-auto pb-px mb-6 border-b border-gray-200">
        {TABS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`shrink-0 px-4 py-2 text-sm font-semibold transition-colors ${
              tab === value
                ? "text-primary border-b-2 border-primary -mb-px bg-primary/5"
                : "text-muted hover:text-navy"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between mb-4 text-xs text-muted">
        <span>
          {data.total} job{data.total !== 1 ? "s" : ""}
        </span>
      </div>

      {data.items.length === 0 ? (
        <p className="text-muted text-center py-12">No jobs found.</p>
      ) : (
        <div className="grid gap-4">
          {data.items.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              allTags={allTags}
              sponsors={sponsors}
              onHide={handleHide}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:border-primary hover:text-primary transition-colors"
          >
            &larr; Prev
          </button>
          <span className="text-sm text-muted px-2">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:border-primary hover:text-primary transition-colors"
          >
            Next &rarr;
          </button>
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/applications/page.tsx
git commit -m "feat(frontend): add Applications page with tab bar filter"
```

---

## Task 7: Navigation Bar

**Files:**
- Create: `frontend/components/Nav.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Create `frontend/components/Nav.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Job Listings" },
  { href: "/applications", label: "Applications" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-3xl mx-auto px-4 flex items-center justify-between h-14">
        <span className="text-navy font-bold text-lg">Aus Job Scraper</span>
        <div className="flex gap-1">
          {LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
                pathname === href
                  ? "text-primary bg-primary/10"
                  : "text-muted hover:text-navy"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Update `frontend/app/layout.tsx`**

Replace the entire file with:

```tsx
import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Aus Job Scraper",
  description: "Seek job listings scraper",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/Nav.tsx frontend/app/layout.tsx
git commit -m "feat(frontend): add top navigation bar"
```

---

## Self-Review

**Spec coverage:**
- [x] Status column with 8 values (SAVED default) — Task 1 + 2
- [x] Status badge on job list (JobCard) — Task 4
- [x] Status editable in detail view (dropdown) — Task 5
- [x] New Applications page (non-SAVED jobs only) — Task 6
- [x] Tab bar filter with default APPLIED — Task 6 (`useState<Tab>("APPLIED")`)
- [x] Hidden jobs excluded from Applications page — Task 6 (`visibility: "visible"` hardcoded)
- [x] Tab: ALL shows all non-SAVED; specific tabs filter by exact status — Task 2 (backend `not_saved`/`status`) + Task 6

**Placeholder scan:** No TBDs, all code is complete.

**Type consistency:**
- `JobStatus` defined in `types.ts`, imported in `StatusBadge.tsx`, `jobs/[id]/page.tsx`, `applications/page.tsx` ✓
- `JOB_STATUSES`, `STATUS_LABELS` exported from `StatusBadge.tsx`, imported in `jobs/[id]/page.tsx` ✓
- `StatusUpdate` schema used in `update_status` route and imported in `routes/jobs.py` ✓
- `status=j.status` passed in `_to_out()` matching `JobOut.status: str` ✓
