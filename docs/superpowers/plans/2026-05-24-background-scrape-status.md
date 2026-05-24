# Background Scrape with Progress Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Seek scrape job as a background task, auto-detect the total number of pages from Seek, and let users monitor progress (current page / total pages) with a cancel button inline below the search form.

**Architecture:** The backend holds a single in-memory state dict for the active scrape job. `POST /api/scrape` starts a background `asyncio` task and returns 202 immediately. On the first page load, `detect_total_pages()` reads Seek's pagination UI and reports the total so users see it right away. `GET /api/scrape/status` returns live progress. `POST /api/scrape/cancel` sets a cancellation flag checked between pages. The frontend polls `/api/scrape/status` every 1 s while status is `running`, showing "Detecting pages..." until total is known.

**Tech Stack:** FastAPI `asyncio.create_task`, Playwright async API, React 19 `useState`/`useEffect`, Tailwind CSS 4, TypeScript 5, Next.js 16 App Router.

---

## Decisions

| Question | Decision |
|----------|----------|
| Update method | Polling — GET /api/scrape/status every 1 s |
| UI placement | Inline below search form with progress bar |
| Cancellation | Yes — Cancel button |
| State persistence | In-memory only (lost on server restart) |
| Page limit | None — detect all pages from Seek automatically; Cancel button handles stopping early |
| Total pages timing | Detect on page 1 load, report immediately; show "Detecting pages..." until then |

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/schemas.py` | Modify | Remove `max_pages` from `ScrapeRequest`; add `ScrapeStatus` |
| `backend/scraper.py` | Modify | Add `detect_total_pages()`, progress callback, cancellation; loop by detected total |
| `backend/routes/scrape.py` | Modify | In-memory state, background task, `/status`, `/cancel` endpoints |
| `backend/tests/test_api.py` | Modify | Tests for status and cancel endpoints |
| `backend/tests/test_scraper.py` | Modify | Tests for `detect_total_pages` |
| `frontend/components/ScrapeProgress.tsx` | Create | Progress bar + Cancel button component |
| `frontend/app/page.tsx` | Modify | Add polling logic, pass status + cancel to SearchForm |
| `frontend/components/SearchForm.tsx` | Modify | Accept `scrapeStatus` + `onCancel` props, render ScrapeProgress |

---

## Progress state machine

```
idle
  → running (POST /api/scrape)
      current_page=0, total_pages=0   → UI: "Detecting pages..."
      current_page=1, total_pages=N   → UI: "Scraping... page 1 of N"
      current_page=2, total_pages=N   → UI: "Scraping... page 2 of N"
      ...
  → done        (scrape finished)
  → cancelled   (cancel requested between pages)
  → error       (exception thrown)
```

`on_progress(page_num, total)` is called **before** processing each page's cards, so users see the current page number update as soon as the browser navigates to it.

---

## Task 1: Update `ScrapeRequest` and add `ScrapeStatus` schema

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# In backend/tests/test_api.py, add:
def test_scrape_status_shape(client):
    res = client.get("/api/scrape/status")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "idle"
    assert body["current_page"] == 0
    assert body["total_pages"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_api.py::test_scrape_status_shape -v
```
Expected: FAIL — 404 (endpoint not yet defined)

- [ ] **Step 3: Update `schemas.py`**

Remove `max_pages` from `ScrapeRequest` and add `ScrapeStatus`:

```python
class ScrapeRequest(BaseModel):
    keywords: str
    location: str
    # max_pages removed — scraper detects all pages from Seek automatically


class ScrapeStatus(BaseModel):
    status: str  # "idle" | "running" | "done" | "cancelled" | "error"
    current_page: int = 0
    total_pages: int = 0
    inserted: int = 0
    updated_reposts: int = 0
    skipped_hidden: int = 0
    error: str | None = None
```

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py backend/tests/test_api.py
git commit -m "test(scrape): add test scaffold for ScrapeStatus shape"
```

---

## Task 2: Add `detect_total_pages` and progress/cancellation to scraper

**Files:**
- Modify: `backend/scraper.py`
- Modify: `backend/tests/test_scraper.py`

The scraper needs to:
1. Detect total pages from Seek's pagination on page 1 load, before processing any cards
2. Loop from page 1 to `total_pages` (detected), not a fixed `max_pages`
3. Accept an `on_progress(current_page: int, total_pages: int)` callback called before processing each page
4. Accept an `is_cancelled()` callable checked between pages

- [ ] **Step 1: Write failing tests**

```python
# In backend/tests/test_scraper.py, add:
import pytest
from unittest.mock import AsyncMock
from scraper import detect_total_pages

@pytest.mark.asyncio
async def test_detect_total_pages_reads_aria_labels():
    mock_page = AsyncMock()
    link1 = AsyncMock()
    link1.get_attribute = AsyncMock(return_value="Page 1")
    link2 = AsyncMock()
    link2.get_attribute = AsyncMock(return_value="Page 4")
    mock_page.query_selector_all = AsyncMock(return_value=[link1, link2])
    result = await detect_total_pages(mock_page)
    assert result == 4

@pytest.mark.asyncio
async def test_detect_total_pages_falls_back_to_one_on_error():
    mock_page = AsyncMock()
    mock_page.query_selector_all = AsyncMock(side_effect=Exception("timeout"))
    result = await detect_total_pages(mock_page)
    assert result == 1

@pytest.mark.asyncio
async def test_detect_total_pages_returns_one_when_no_links():
    mock_page = AsyncMock()
    mock_page.query_selector_all = AsyncMock(return_value=[])
    result = await detect_total_pages(mock_page)
    assert result == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_scraper.py::test_detect_total_pages_reads_aria_labels tests/test_scraper.py::test_detect_total_pages_falls_back_to_one_on_error tests/test_scraper.py::test_detect_total_pages_returns_one_when_no_links -v
```
Expected: FAIL — `ImportError: cannot import name 'detect_total_pages'`

- [ ] **Step 3: Add `detect_total_pages` to `scraper.py`**

Add after the `SEEK_BASE` constant:

```python
async def detect_total_pages(page) -> int:
    """Read total page count from Seek's pagination. Returns 1 on failure."""
    try:
        links = await page.query_selector_all("a[aria-label^='Page ']")
        nums = []
        for link in links:
            label = await link.get_attribute("aria-label")
            if label:
                m = re.match(r"Page (\d+)", label)
                if m:
                    nums.append(int(m.group(1)))
        if nums:
            return max(nums)
    except Exception:
        pass
    return 1
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_scraper.py::test_detect_total_pages_reads_aria_labels tests/test_scraper.py::test_detect_total_pages_falls_back_to_one_on_error tests/test_scraper.py::test_detect_total_pages_returns_one_when_no_links -v
```
Expected: PASS

- [ ] **Step 5: Update `scrape_seek` — remove `max_pages`, add loop by detected total, add callback/cancellation**

Replace the entire `scrape_seek` function (keep the card-parsing body unchanged, only the outer loop and signature change):

```python
async def scrape_seek(
    keywords: str,
    location: str,
    on_progress=None,   # callable(current_page: int, total_pages: int)
    is_cancelled=None,  # callable() -> bool
) -> list[ScrapedJob]:
    """Scrape all Seek pages for the given search. Detects total pages from Seek's pagination."""
    results: list[ScrapedJob] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(20000)

        total_pages = 1  # updated after page 1 loads
        page_num = 1

        while page_num <= total_pages:
            if is_cancelled and is_cancelled():
                break

            url = build_seek_url(keywords, location, page_num)
            await page.goto(url, wait_until="domcontentloaded")

            if page_num == 1:
                total_pages = await detect_total_pages(page)

            if on_progress:
                on_progress(page_num, total_pages)

            job_cards = await page.query_selector_all("article[data-testid='job-card']")
            if not job_cards:
                break

            for card in job_cards:
                try:
                    title_el = await card.query_selector("a[data-testid='job-card-title']")
                    title = await title_el.inner_text() if title_el else None
                    href = await title_el.get_attribute("href") if title_el else None
                    clean_path = href.split("?")[0] if href else None
                    seek_url = f"{SEEK_BASE}{clean_path}" if clean_path and clean_path.startswith("/") else clean_path

                    company_el = await card.query_selector("a[data-automation='jobCompany']")
                    company = await company_el.inner_text() if company_el else None

                    loc_els = await card.query_selector_all("[data-automation='jobLocation']")
                    location_text = " ".join([await e.inner_text() for e in loc_els])
                    loc = parse_location(location_text)

                    salary_el = await card.query_selector("[data-automation='jobSalary']")
                    salary_range = await salary_el.inner_text() if salary_el else None

                    date_el = await card.query_selector("[data-automation='jobListingDate']")
                    date_text = (await date_el.inner_text()).strip() if date_el else ""
                    listed_date = parse_listing_date(date_text)

                    if title and seek_url:
                        results.append(ScrapedJob(
                            seek_url=seek_url,
                            title=title.strip(),
                            company=company.strip() if company else None,
                            state=loc["state"],
                            city=loc["city"],
                            suburb=loc["suburb"],
                            salary_range=salary_range.strip() if salary_range else None,
                            listed_date=listed_date,
                        ))
                except Exception:
                    continue

            page_num += 1

        for job in results:
            try:
                await page.goto(job.seek_url, wait_until="domcontentloaded")
                desc_el = await page.query_selector("[data-automation='jobAdDetails']")
                if desc_el:
                    job.description = (await desc_el.inner_text()).strip()
            except Exception:
                pass

        await browser.close()
    return results
```

> Note: The card-parsing body (inner `for card in job_cards` loop) is identical to the current `scraper.py:52–87`. The only structural changes are the new signature, the `while` loop replacing `for page_num in range(...)`, the `detect_total_pages` call after page 1 loads, the `on_progress` call before card parsing, and the `is_cancelled` check at the top of each iteration.

- [ ] **Step 6: Commit**

```bash
git add backend/scraper.py backend/tests/test_scraper.py
git commit -m "feat(scraper): detect total pages from Seek, add progress callback and cancellation"
```

---

## Task 3: Refactor scrape route — background task, status, cancel endpoints

**Files:**
- Modify: `backend/routes/scrape.py`

Replace the synchronous `trigger_scrape` with three endpoints:
- `POST /api/scrape` → starts background task, returns 202
- `GET /api/scrape/status` → returns `ScrapeStatus`
- `POST /api/scrape/cancel` → sets cancellation flag

- [ ] **Step 1: Write failing tests**

```python
# In backend/tests/test_api.py, add:
def test_scrape_status_idle_on_startup(client):
    res = client.get("/api/scrape/status")
    assert res.status_code == 200
    assert res.json()["status"] == "idle"

def test_scrape_cancel_when_idle_returns_200(client):
    res = client.post("/api/scrape/cancel")
    assert res.status_code == 200

def test_scrape_returns_202(client, monkeypatch):
    async def fake_scrape(*args, **kwargs):
        return []
    monkeypatch.setattr("routes.scrape.scrape_seek", fake_scrape)
    res = client.post("/api/scrape", json={"keywords": "python", "location": "Sydney"})
    assert res.status_code == 202

def test_scrape_returns_409_when_already_running(client, monkeypatch):
    import routes.scrape as scrape_module
    scrape_module._state["status"] = "running"
    res = client.post("/api/scrape", json={"keywords": "python", "location": "Sydney"})
    assert res.status_code == 409
    scrape_module._state["status"] = "idle"  # reset
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_api.py::test_scrape_status_idle_on_startup tests/test_api.py::test_scrape_cancel_when_idle_returns_200 tests/test_api.py::test_scrape_returns_202 tests/test_api.py::test_scrape_returns_409_when_already_running -v
```
Expected: FAIL

- [ ] **Step 3: Rewrite `routes/scrape.py`**

```python
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from models import Job
from schemas import ScrapeRequest, ScrapeStatus
from scraper import scrape_seek

router = APIRouter()

_state: dict = {
    "status": "idle",
    "current_page": 0,
    "total_pages": 0,
    "inserted": 0,
    "updated_reposts": 0,
    "skipped_hidden": 0,
    "error": None,
    "cancel_requested": False,
}


def _reset_state() -> None:
    _state.update({
        "status": "running",
        "current_page": 0,
        "total_pages": 0,
        "inserted": 0,
        "updated_reposts": 0,
        "skipped_hidden": 0,
        "error": None,
        "cancel_requested": False,
    })


def _on_progress(current: int, total: int) -> None:
    _state["current_page"] = current
    _state["total_pages"] = total


def _is_cancelled() -> bool:
    return _state["cancel_requested"]


async def _run_scrape(req: ScrapeRequest) -> None:
    from database import engine
    try:
        jobs = await scrape_seek(
            req.keywords,
            req.location,
            on_progress=_on_progress,
            is_cancelled=_is_cancelled,
        )

        if _state["cancel_requested"]:
            _state["status"] = "cancelled"
            return

        with Session(engine) as session:
            for scraped in jobs:
                existing = session.exec(
                    select(Job).where(Job.seek_url == scraped.seek_url)
                ).first()

                if existing:
                    if existing.is_hidden:
                        _state["skipped_hidden"] += 1
                        continue
                    dates = json.loads(existing.listed_dates or "[]")
                    if scraped.listed_date not in dates:
                        dates.append(scraped.listed_date)
                        existing.listed_dates = json.dumps(dates)
                        existing.latest_listing_date = max(dates)
                        existing.is_repost = True
                        _state["updated_reposts"] += 1
                else:
                    dates = [scraped.listed_date]
                    job = Job(
                        seek_url=scraped.seek_url,
                        title=scraped.title,
                        company=scraped.company,
                        description=scraped.description,
                        state=scraped.state,
                        city=scraped.city,
                        suburb=scraped.suburb,
                        salary_range=scraped.salary_range,
                        listed_dates=json.dumps(dates),
                        latest_listing_date=scraped.listed_date,
                    )
                    session.add(job)
                    _state["inserted"] += 1
            session.commit()

        _state["status"] = "done"

    except Exception as exc:
        _state["status"] = "error"
        _state["error"] = str(exc)


@router.post("/scrape", status_code=202)
async def trigger_scrape(req: ScrapeRequest) -> dict:
    if _state["status"] == "running":
        return JSONResponse(status_code=409, content={"detail": "Scrape already running"})
    _reset_state()
    asyncio.create_task(_run_scrape(req))
    return {"status": "started"}


@router.get("/scrape/status", response_model=ScrapeStatus)
def get_scrape_status() -> ScrapeStatus:
    return ScrapeStatus(
        status=_state["status"],
        current_page=_state["current_page"],
        total_pages=_state["total_pages"],
        inserted=_state["inserted"],
        updated_reposts=_state["updated_reposts"],
        skipped_hidden=_state["skipped_hidden"],
        error=_state["error"],
    )


@router.post("/scrape/cancel")
def cancel_scrape() -> dict:
    _state["cancel_requested"] = True
    return {"status": "cancel_requested"}
```

> Note: This replaces the entire file. The DB upsert logic is lifted from the old `trigger_scrape` with counter references changed to `_state[...]`. No `max_pages` is passed to `scrape_seek` — it detects pages automatically.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_api.py::test_scrape_status_idle_on_startup tests/test_api.py::test_scrape_cancel_when_idle_returns_200 tests/test_api.py::test_scrape_returns_202 tests/test_api.py::test_scrape_returns_409_when_already_running -v
```
Expected: PASS

- [ ] **Step 5: Run full backend test suite to check for regressions**

```bash
cd backend && uv run pytest tests/ -v
```
Expected: All pass (or pre-existing failures only)

- [ ] **Step 6: Commit**

```bash
git add backend/routes/scrape.py backend/schemas.py backend/tests/test_api.py
git commit -m "feat(scrape): run scrape as background task with status/cancel endpoints"
```

---

## Task 4: Create `ScrapeProgress` frontend component

**Files:**
- Create: `frontend/components/ScrapeProgress.tsx`

Purely presentational. Shows "Detecting pages..." when `total_pages=0`, a progress bar + current/total once detection is done, and a Cancel button while running.

- [ ] **Step 1: Create `frontend/components/ScrapeProgress.tsx`**

```tsx
interface Props {
  status: string;
  currentPage: number;
  totalPages: number;
  onCancel: () => void;
}

export default function ScrapeProgress({ status, currentPage, totalPages, onCancel }: Props) {
  if (status === "idle") return null;

  const isRunning = status === "running";
  const detecting = isRunning && totalPages === 0;
  const pct = totalPages > 0 ? Math.round((currentPage / totalPages) * 100) : 0;

  let label: string;
  if (detecting) {
    label = "Detecting pages...";
  } else if (isRunning) {
    label = `Scraping... page ${currentPage} of ${totalPages}`;
  } else if (status === "done") {
    label = "Scrape complete";
  } else if (status === "cancelled") {
    label = "Scrape cancelled";
  } else {
    label = "Scrape failed";
  }

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center justify-between text-sm text-[#888888]">
        <span>{label}</span>
        {isRunning && (
          <button
            onClick={onCancel}
            className="text-xs text-[#753991] hover:underline"
          >
            Cancel
          </button>
        )}
      </div>

      {!detecting && (isRunning || status === "done") && (
        <div className="h-1.5 w-full rounded-full bg-gray-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-[#209dd7] transition-all duration-300"
            style={{ width: `${status === "done" ? 100 : pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/ScrapeProgress.tsx
git commit -m "feat(ui): add ScrapeProgress with detecting/progress/cancel states"
```

---

## Task 5: Wire polling into `page.tsx`

**Files:**
- Modify: `frontend/app/page.tsx`

The home page starts polling when a scrape is triggered and stops when status becomes `done`, `cancelled`, or `error`. On `done`, it triggers a job list refresh (existing `refreshKey` pattern). No `max_pages` is sent in the POST body.

- [ ] **Step 1: Update `frontend/app/page.tsx`**

```tsx
"use client";
import { useState, useEffect, useRef } from "react";
import SearchForm from "@/components/SearchForm";
import JobList from "@/components/JobList";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ScrapeStatus {
  status: string;
  current_page: number;
  total_pages: number;
  inserted: number;
  updated_reposts: number;
  skipped_hidden: number;
  error: string | null;
}

const IDLE_STATUS: ScrapeStatus = {
  status: "idle",
  current_page: 0,
  total_pages: 0,
  inserted: 0,
  updated_reposts: 0,
  skipped_hidden: 0,
  error: null,
};

export default function HomePage() {
  const [scrapeStatus, setScrapeStatus] = useState<ScrapeStatus>(IDLE_STATUS);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const startPolling = () => {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/scrape/status`);
        if (!res.ok) return;
        const data: ScrapeStatus = await res.json();
        setScrapeStatus(data);
        if (data.status !== "running") {
          stopPolling();
          if (data.status === "done") setRefreshKey((k) => k + 1);
        }
      } catch {
        // network blip — keep polling
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

  const scrapeMsg =
    scrapeStatus.status === "done"
      ? `Done — ${scrapeStatus.inserted} new, ${scrapeStatus.updated_reposts} reposted`
      : scrapeStatus.status === "error"
      ? `Error: ${scrapeStatus.error}`
      : null;

  return (
    <main className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-[#032147]">Aus Job Scraper</h1>
          <p className="text-[#888888] mt-1">Find and track jobs from Seek</p>
        </div>

        <SearchForm
          onScrape={handleScrape}
          scrapeStatus={scrapeStatus}
          onCancel={handleCancel}
        />

        {error && <p className="text-red-500 text-sm">{error}</p>}
        {scrapeMsg && <p className="text-sm text-[#888888]">{scrapeMsg}</p>}

        <JobList refreshKey={refreshKey} />
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(ui): add polling for scrape status in homepage"
```

---

## Task 6: Update `SearchForm` to accept and display scrape progress

**Files:**
- Modify: `frontend/components/SearchForm.tsx`

Add `scrapeStatus` and `onCancel` props. Render `ScrapeProgress` below the form. Disable the Scrape button while running.

- [ ] **Step 1: Update `frontend/components/SearchForm.tsx`**

```tsx
"use client";
import { useState } from "react";
import ScrapeProgress from "./ScrapeProgress";

interface ScrapeStatus {
  status: string;
  current_page: number;
  total_pages: number;
}

interface Props {
  onScrape: (keywords: string, location: string) => void;
  scrapeStatus: ScrapeStatus;
  onCancel: () => void;
}

export default function SearchForm({ onScrape, scrapeStatus, onCancel }: Props) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const isRunning = scrapeStatus.status === "running";

  return (
    <div className="bg-white rounded-2xl shadow p-6">
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          className="flex-1 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#209dd7]"
          placeholder="Keywords (e.g. Python developer)"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
        />
        <input
          className="flex-1 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#209dd7]"
          placeholder="Location (e.g. Sydney)"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
        />
        <button
          onClick={() => onScrape(keywords, location)}
          disabled={isRunning}
          className="bg-[#753991] text-white rounded-lg px-6 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {isRunning ? "Scraping..." : "Scrape"}
        </button>
      </div>

      <ScrapeProgress
        status={scrapeStatus.status}
        currentPage={scrapeStatus.current_page}
        totalPages={scrapeStatus.total_pages}
        onCancel={onCancel}
      />
    </div>
  );
}
```

> Note: Check the current `SearchForm.tsx` for any additional markup not shown here and preserve it.

- [ ] **Step 2: Commit**

```bash
git add frontend/components/SearchForm.tsx
git commit -m "feat(ui): wire ScrapeProgress into SearchForm with cancel support"
```

---

## Verification

### Backend
```bash
cd backend && uv run pytest tests/ -v
```
All tests pass.

Manual check — start the API server and call endpoints:
```bash
cd backend && uv run uvicorn main:app --reload
# In another terminal:
curl -s http://localhost:8000/api/scrape/status
# Expected: {"status":"idle","current_page":0,"total_pages":0,...}

curl -s -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"keywords":"python","location":"Sydney"}'
# Expected: {"status":"started"} with HTTP 202

# Poll a few times:
curl -s http://localhost:8000/api/scrape/status
# Expected while running: {"status":"running","current_page":1,"total_pages":8,...}

curl -s -X POST http://localhost:8000/api/scrape/cancel
# Expected: {"status":"cancel_requested"}
```

### Frontend
```bash
cd frontend && npm run dev
```
1. Open http://localhost:3000
2. Enter keywords + location, click Scrape
3. "Detecting pages..." appears below the form
4. Within a few seconds, changes to "Scraping... page 1 of N" with a progress bar
5. Progress bar advances as each page completes
6. Cancel button is visible; clicking it stops the scrape between pages
7. On completion, job list auto-refreshes and "Done — X new, Y reposted" appears
8. Scrape button is disabled while scraping, re-enables after

---

## Notes

- **Total pages fallback**: `detect_total_pages` reads `aria-label="Page N"` from Seek's pagination. Falls back to `1` if the selector doesn't match — meaning the scraper treats it as a single-page result. The selector may need tuning after live testing.
- **Single concurrent scrape**: `POST /api/scrape` returns 409 if a scrape is already running.
- **In-memory only**: `_state` is a module-level dict. Restarting the server resets it to idle.
- **DB session in background task**: `_run_scrape` opens its own `Session(engine)` — required since it runs outside the request lifecycle.
- **`max_pages` removed everywhere**: `ScrapeRequest`, `scrape_seek` signature, and the frontend POST body no longer include `max_pages`.
