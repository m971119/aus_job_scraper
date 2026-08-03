# Scraper Page + URL Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the scraper UI to a dedicated `/scraper` route and add a URL import feature that crawls a single Seek job URL, deduplicates against the DB, and navigates to the result.

**Architecture:** Split `page.tsx` into two routes — `/` keeps only the job list, `/scraper` gets the bulk scraper UI plus a new `UrlImport` component. The backend gets a new `POST /api/scrape/url` endpoint that normalises the URL, checks the DB, then crawls with Playwright if not found.

**Tech Stack:** FastAPI, SQLModel, Playwright (Python), Next.js 15 App Router (TypeScript)

---

## File Map

**Create:**
- `backend/schemas.py` — add `UrlImportRequest`, `UrlImportResponse`
- `backend/scraper.py` — add `scrape_job_url(url: str) -> ScrapedJob`
- `backend/routes/scrape.py` — add `POST /api/scrape/url`
- `frontend/app/scraper/page.tsx` — new Scraper page (bulk scraper + URL import)
- `frontend/components/UrlImport.tsx` — URL import UI component

**Modify:**
- `frontend/app/page.tsx` — strip scraper UI, keep only job list
- `frontend/components/Nav.tsx` — add "Scraper" nav link

---

### Task 1: Add backend schemas

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add `UrlImportRequest` and `UrlImportResponse` to schemas**

Open `backend/schemas.py` and append at the end:

```python
class UrlImportRequest(BaseModel):
    url: str


class UrlImportResponse(BaseModel):
    exists: bool
    job_id: int
```

- [ ] **Step 2: Commit**

```bash
git add backend/schemas.py
git commit -m "feat(scraper): add UrlImport request/response schemas"
```

---

### Task 2: Add `scrape_job_url` to scraper

**Files:**
- Modify: `backend/scraper.py`

- [ ] **Step 1: Add `scrape_job_url` function**

Append to `backend/scraper.py`:

```python
async def scrape_job_url(url: str) -> ScrapedJob:
    """Scrape title, company, location and description from a single Seek job page."""
    from datetime import date
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        page.set_default_timeout(20000)
        await page.goto(url, wait_until="domcontentloaded")

        title_el = await page.query_selector("h1[data-automation='job-detail-title']")
        title = (await title_el.inner_text()).strip() if title_el else "Unknown"

        company_el = await page.query_selector("[data-automation='advertiser-name']")
        company = (await company_el.inner_text()).strip() if company_el else None

        loc_els = await page.query_selector_all("[data-automation='job-detail-location']")
        location_text = " ".join([(await e.inner_text()) for e in loc_els])
        loc = parse_location(location_text) if location_text.strip() else {"state": None, "city": None, "suburb": None}

        salary_el = await page.query_selector("[data-automation='job-detail-salary']")
        salary_range = (await salary_el.inner_text()).strip() if salary_el else None

        desc_el = await page.query_selector("[data-automation='jobAdDetails']")
        description = (await desc_el.inner_text()).strip() if desc_el else None

        await context.close()
        await browser.close()

    from urllib.parse import urlparse
    path = urlparse(url).path.rstrip("/")

    return ScrapedJob(
        seek_url=path,
        title=title,
        company=company,
        description=description,
        state=loc["state"],
        city=loc["city"],
        suburb=loc["suburb"],
        salary_range=salary_range,
        listed_date=date.today().isoformat(),
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/scraper.py
git commit -m "feat(scraper): add scrape_job_url for single-URL import"
```

---

### Task 3: Add `POST /api/scrape/url` endpoint

**Files:**
- Modify: `backend/routes/scrape.py`

- [ ] **Step 1: Add imports at the top of `backend/routes/scrape.py`**

The file already imports `json`, `Session`, `select`, `Job`. Add `Depends`, `HTTPException` to the FastAPI import and the new schemas:

```python
from fastapi import APIRouter, Depends, HTTPException
```

Add `get_session` dependency (after existing imports):

```python
from database import engine


def get_session():
    with Session(engine) as session:
        yield session
```

- [ ] **Step 2: Add the URL import endpoint**

Append to `backend/routes/scrape.py`:

```python
@router.post("/scrape/url", response_model=UrlImportResponse)
async def import_from_url(
    req: UrlImportRequest,
    session: Session = Depends(get_session),
):
    from urllib.parse import urlparse
    parsed = urlparse(req.url)
    if "seek.com.au" not in parsed.netloc:
        raise HTTPException(status_code=422, detail="URL must be a seek.com.au job URL")

    path = parsed.path.rstrip("/")
    existing = session.exec(select(Job).where(Job.seek_url == path)).first()
    if existing:
        return UrlImportResponse(exists=True, job_id=existing.id)

    scraped = await scrape_job_url(req.url)

    # Re-check after scrape in case seek_url differs from the entered URL
    existing = session.exec(select(Job).where(Job.seek_url == scraped.seek_url)).first()
    if existing:
        return UrlImportResponse(exists=True, job_id=existing.id)

    job = Job(
        seek_url=scraped.seek_url,
        seek_urls=json.dumps([scraped.seek_url]),
        title=scraped.title,
        company=scraped.company,
        description=scraped.description,
        state=scraped.state,
        city=scraped.city,
        suburb=scraped.suburb,
        salary_range=scraped.salary_range,
        listed_dates=json.dumps([scraped.listed_date]),
        latest_listing_date=scraped.listed_date,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return UrlImportResponse(exists=False, job_id=job.id)
```

Also add to the imports at the top of the file:

```python
from schemas import ScrapeRequest, ScrapeStatus, UrlImportRequest, UrlImportResponse
from scraper import scrape_seek, scrape_job_url
```

- [ ] **Step 3: Verify the backend starts without errors**

```bash
cd backend && uv run uvicorn main:app --port 8000
```

Expected: server starts, no import errors. Stop with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add backend/routes/scrape.py
git commit -m "feat(scraper): add POST /api/scrape/url endpoint"
```

---

### Task 4: Add `UrlImport` frontend component

**Files:**
- Create: `frontend/components/UrlImport.tsx`

- [ ] **Step 1: Create `frontend/components/UrlImport.tsx`**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function UrlImport() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingId, setExistingId] = useState<number | null>(null);

  const handleImport = async () => {
    if (!url.trim()) return;
    setError(null);
    setExistingId(null);
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/scrape/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!res.ok) {
        const e = await res.json();
        setError(e.detail ?? "Import failed");
        return;
      }
      const data: { exists: boolean; job_id: number } = await res.json();
      if (data.exists) {
        setExistingId(data.job_id);
      } else {
        router.push(`/jobs/${data.job_id}`);
      }
    } catch {
      setError("Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-5 bg-white rounded-xl border border-gray-100 shadow-sm">
      <h2 className="text-sm font-semibold text-navy mb-3">Import from URL</h2>
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => { setUrl(e.target.value); setExistingId(null); setError(null); }}
          onKeyDown={(e) => { if (e.key === "Enter") handleImport(); }}
          placeholder="https://www.seek.com.au/job/..."
          disabled={loading}
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        <button
          onClick={handleImport}
          disabled={!url.trim() || loading}
          className="text-xs font-semibold bg-secondary text-white px-3 py-1.5 rounded-lg hover:opacity-90 disabled:opacity-40"
        >
          {loading ? "Importing..." : "Import"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      {existingId && (
        <p className="mt-2 text-xs text-muted">
          This job already exists.{" "}
          <a href={`/jobs/${existingId}`} className="text-primary hover:underline">
            View job
          </a>
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/UrlImport.tsx
git commit -m "feat(scraper): add UrlImport component"
```

---

### Task 5: Create `/scraper` page

**Files:**
- Create: `frontend/app/scraper/page.tsx`

- [ ] **Step 1: Create `frontend/app/scraper/page.tsx`**

This is the current `page.tsx` scraper logic (polling, SearchForm, ScrapeProgress) plus `UrlImport`:

```tsx
"use client";
import { useState, useEffect, useRef } from "react";
import SearchForm from "@/components/SearchForm";
import UrlImport from "@/components/UrlImport";
import { ScrapeStatus } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const IDLE_STATUS: ScrapeStatus = {
  status: "idle",
  phase: "seeking",
  current_page: 0,
  jobs_scraped: 0,
  jobs_compared: 0,
  inserted: 0,
  updated_reposts: 0,
  skipped_hidden: 0,
  error: null,
};

const POLL_INTERVAL = 3;

export default function ScraperPage() {
  const [scrapeStatus, setScrapeStatus] = useState<ScrapeStatus>(IDLE_STATUS);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(0);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const countdownRef = useRef(0);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setCountdown(0);
  };

  const doPoll = async () => {
    try {
      const res = await fetch(`${API}/api/scrape/status`);
      if (!res.ok) return;
      const data: ScrapeStatus = await res.json();
      setScrapeStatus(data);
      if (data.status !== "running") {
        stopPolling();
        if (data.status === "cancelled") setTimeout(() => setScrapeStatus(IDLE_STATUS), 2000);
      }
    } catch {
      // network blip — keep polling
    }
  };

  const startPolling = () => {
    stopPolling();
    doPoll();
    countdownRef.current = POLL_INTERVAL;
    setCountdown(POLL_INTERVAL);
    pollingRef.current = setInterval(() => {
      countdownRef.current -= 1;
      if (countdownRef.current <= 0) {
        countdownRef.current = POLL_INTERVAL;
        setCountdown(POLL_INTERVAL);
        doPoll();
      } else {
        setCountdown(countdownRef.current);
      }
    }, 1000);
  };

  useEffect(() => () => stopPolling(), []);

  const handleScrape = async (keywords: string, location: string) => {
    setError(null);
    try {
      const res = await fetch(`${API}/api/scrape`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords, location }),
      });
      if (res.status === 409) {
        setError("A scrape is already running.");
        return;
      }
      if (!res.ok) throw new Error(`Scrape failed: ${res.status}`);
      setScrapeStatus({ ...IDLE_STATUS, status: "running" });
      startPolling();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  };

  const handleCancel = async () => {
    await fetch(`${API}/api/scrape/cancel`, { method: "POST" });
  };

  function scrapeMessage(): string | null {
    if (scrapeStatus.status === "done") {
      return `Done — ${scrapeStatus.inserted} new, ${scrapeStatus.updated_reposts} reposted`;
    }
    if (scrapeStatus.status === "error") {
      return `Error: ${scrapeStatus.error}`;
    }
    return null;
  }
  const scrapeMsg = scrapeMessage();

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-8">
        <div className="h-1 w-16 bg-accent rounded mb-4" />
        <h1 className="text-3xl font-bold text-navy">Scraper</h1>
        <p className="text-muted mt-1">Search and scrape recent jobs from Seek.com.au</p>
      </div>

      <div className="space-y-4">
        <div className="p-5 bg-white rounded-xl border border-gray-100 shadow-sm">
          <SearchForm
            onScrape={handleScrape}
            scrapeStatus={scrapeStatus}
            onCancel={handleCancel}
            countdown={countdown}
          />
          {error && <p className="mt-3 text-red-500 text-sm">{error}</p>}
          {scrapeMsg && <p className="mt-3 text-green-600 text-sm">{scrapeMsg}</p>}
        </div>

        <UrlImport />
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/scraper/page.tsx
git commit -m "feat(scraper): add /scraper page with bulk scraper and URL import"
```

---

### Task 6: Simplify `/` (home) page

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Replace `frontend/app/page.tsx` with jobs-only content**

```tsx
"use client";
import { useState, useCallback, useRef, Suspense } from "react";
import JobList from "@/components/JobList";

export default function HomePage() {
  const [hasFilters, setHasFilters] = useState(false);
  const resetFiltersRef = useRef<() => void>(() => {});

  const handleFilterStateChange = useCallback((has: boolean, reset: () => void) => {
    setHasFilters(has);
    resetFiltersRef.current = reset;
  }, []);

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-8">
        <div className="h-1 w-16 bg-accent rounded mb-4" />
        <h1 className="text-3xl font-bold text-navy">Job Listings</h1>
        <p className="text-muted mt-1">Your saved jobs from Seek.com.au</p>
      </div>

      <div className="flex items-center gap-3 mb-4">
        {hasFilters && (
          <button
            onClick={() => resetFiltersRef.current()}
            className="px-3 py-1 text-xs border border-gray-200 rounded-lg text-muted hover:border-primary hover:text-primary transition-colors"
          >
            Reset filters
          </button>
        )}
      </div>

      <Suspense>
        <JobList refreshKey={0} onFilterStateChange={handleFilterStateChange} />
      </Suspense>
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "refactor(home): remove scraper UI, keep job list only"
```

---

### Task 7: Add Scraper nav link

**Files:**
- Modify: `frontend/components/Nav.tsx`

- [ ] **Step 1: Add "Scraper" to nav and update `isActive`**

Replace the nav links array and `isActive` in `frontend/components/Nav.tsx`:

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Nav() {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" || pathname.startsWith("/jobs") : pathname.startsWith(href);

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-3xl mx-auto px-4 flex items-center justify-between h-14">
        <span className="text-navy font-bold text-lg">Aus Job Scraper</span>
        <div className="flex gap-1">
          {[
            { href: "/", label: "Job Listings" },
            { href: "/scraper", label: "Scraper" },
            { href: "/applications", label: "Applications" },
            { href: "/resume", label: "Resume" },
            { href: "/ai-filter", label: "AI Filter" },
          ].map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
                isActive(href)
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

- [ ] **Step 2: Commit**

```bash
git add frontend/components/Nav.tsx
git commit -m "feat(nav): add Scraper link"
```
