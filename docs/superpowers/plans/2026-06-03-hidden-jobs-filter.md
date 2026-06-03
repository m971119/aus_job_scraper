# Hidden Jobs Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a visibility filter to the job list that lets users see hidden jobs and unhide them.

**Architecture:** Backend `GET /api/jobs` gains a `visibility` query param (`visible`/`hidden`/`all`) that replaces the hard-coded `is_hidden == False` filter. A new `PATCH /unhide` endpoint mirrors the existing `/hide` endpoint. The frontend adds a visibility select to the filter bar and an unhide button to `JobCard`.

**Tech Stack:** FastAPI (Python), SQLModel, Next.js 14, Tailwind CSS

---

### Task 1: Backend — visibility filter and unhide endpoint

**Files:**
- Modify: `backend/routes/jobs.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_api.py`:

```python
def test_visibility_hidden_returns_only_hidden():
    with Session(engine) as s:
        s.add(make_job(seek_url="https://seek.com.au/job/1", title="Visible"))
        j = make_job(seek_url="https://seek.com.au/job/2", title="Hidden")
        j.is_hidden = True
        s.add(j)
        s.commit()

    resp = client.get("/api/jobs?visibility=hidden")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Hidden"
    assert data["items"][0]["is_hidden"] is True


def test_visibility_all_returns_all_jobs():
    with Session(engine) as s:
        s.add(make_job(seek_url="https://seek.com.au/job/1", title="Visible"))
        j = make_job(seek_url="https://seek.com.au/job/2", title="Hidden")
        j.is_hidden = True
        s.add(j)
        s.commit()

    resp = client.get("/api/jobs?visibility=all")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_visibility_visible_is_default():
    with Session(engine) as s:
        s.add(make_job(seek_url="https://seek.com.au/job/1", title="Visible"))
        j = make_job(seek_url="https://seek.com.au/job/2", title="Hidden")
        j.is_hidden = True
        s.add(j)
        s.commit()

    resp = client.get("/api/jobs")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "Visible"


def test_unhide_job():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Was Hidden")
        j.is_hidden = True
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    resp = client.patch(f"/api/jobs/{job_id}/unhide")
    assert resp.status_code == 200
    assert resp.json()["is_hidden"] is False

    list_resp = client.get("/api/jobs")
    titles = [j["title"] for j in list_resp.json()["items"]]
    assert "Was Hidden" in titles


def test_unhide_job_not_found():
    resp = client.patch("/api/jobs/99999/unhide")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && uv run pytest tests/test_api.py::test_visibility_hidden_returns_only_hidden tests/test_api.py::test_visibility_all_returns_all_jobs tests/test_api.py::test_visibility_visible_is_default tests/test_api.py::test_unhide_job tests/test_api.py::test_unhide_job_not_found -v
```

Expected: all 5 FAIL (unknown param / endpoint not found).

- [ ] **Step 3: Implement visibility filter and unhide endpoint**

Replace `backend/routes/jobs.py` with:

```python
import json
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlmodel import Session, col, select
from database import engine
from models import Job, JobTag, Tag
from schemas import JobOut, JobsPage, TagOut
from scraper import SEEK_BASE

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    include_tag: Optional[str] = Query(None),
    exclude_tag: Optional[str] = Query(None),
    is_repost: Literal["all", "originals", "reposts"] = Query("all"),
    visibility: Literal["visible", "hidden", "all"] = Query("visible"),
    sort: Literal["latest", "oldest"] = Query("latest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
):
    query = select(Job)
    if visibility == "visible":
        query = query.where(Job.is_hidden == False)  # noqa: E712
    elif visibility == "hidden":
        query = query.where(Job.is_hidden == True)  # noqa: E712

    if keyword:
        kw = f"%{keyword}%"
        query = query.where(
            or_(col(Job.title).ilike(kw), col(Job.description).ilike(kw))
        )

    if location:
        loc = f"%{location}%"
        query = query.where(
            or_(
                col(Job.city).ilike(loc),
                col(Job.state).ilike(loc),
                col(Job.suburb).ilike(loc),
            )
        )

    include_tags = [t.strip() for t in include_tag.split(",") if t.strip()] if include_tag else []
    exclude_tags = [t.strip() for t in exclude_tag.split(",") if t.strip()] if exclude_tag else []

    if include_tags:
        include_subq = (
            select(JobTag.job_id)
            .join(Tag, JobTag.tag_id == Tag.id)
            .where(or_(*[Tag.name.ilike(t) for t in include_tags]))
        )
        query = query.where(Job.id.in_(include_subq))

    for exc in exclude_tags:
        exclude_subq = (
            select(JobTag)
            .join(Tag, JobTag.tag_id == Tag.id)
            .where(JobTag.job_id == Job.id)
            .where(Tag.name.ilike(exc))
        ).exists()
        query = query.where(~exclude_subq)

    if is_repost == "originals":
        query = query.where(Job.is_repost == False)  # noqa: E712
    elif is_repost == "reposts":
        query = query.where(Job.is_repost == True)  # noqa: E712

    total = session.exec(select(func.count()).select_from(query.subquery())).one()

    order = col(Job.latest_listing_date).desc() if sort == "latest" else col(Job.latest_listing_date).asc()
    jobs = session.exec(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()

    return JobsPage(items=[_to_out(j, session) for j in jobs], total=total, page=page, page_size=page_size)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_out(job, session)


@router.patch("/jobs/{job_id}/hide", response_model=JobOut)
def hide_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_hidden = True
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)


@router.patch("/jobs/{job_id}/unhide", response_model=JobOut)
def unhide_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_hidden = False
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)


def _get_job_tags(session: Session, job_id: int) -> list[TagOut]:
    rows = session.exec(select(Tag).join(JobTag).where(JobTag.job_id == job_id)).all()
    return [TagOut(id=t.id, name=t.name) for t in rows]


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
        tags=_get_job_tags(session, j.id),
    )
```

- [ ] **Step 4: Run all new tests to confirm they pass**

```bash
cd backend && uv run pytest tests/test_api.py::test_visibility_hidden_returns_only_hidden tests/test_api.py::test_visibility_all_returns_all_jobs tests/test_api.py::test_visibility_visible_is_default tests/test_api.py::test_unhide_job tests/test_api.py::test_unhide_job_not_found -v
```

Expected: all 5 PASS.

- [ ] **Step 5: Run full test suite to check no regressions**

```bash
cd backend && uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/jobs.py backend/tests/test_api.py
git commit -m "feat(jobs): add visibility filter and unhide endpoint"
```

---

### Task 2: Frontend — JobCard unhide button

**Files:**
- Modify: `frontend/components/JobCard.tsx`

- [ ] **Step 1: Add `onUnhide` prop and conditional button**

In `frontend/components/JobCard.tsx`, update the `Props` interface and the bottom action bar:

```tsx
interface Props {
  job: Job;
  allTags: Tag[];
  sponsors: string[];
  onHide?: (id: number) => void;
  onUnhide?: (id: number) => void;
}

export default function JobCard({ job, allTags, sponsors, onHide, onUnhide }: Props) {
```

Replace the bottom action bar (the `<div className="mt-4 pt-4 ...">` block) with:

```tsx
      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
        <Link
          href={`/jobs/${job.id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-sm font-semibold text-primary border border-primary px-3 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-colors"
        >
          View details
        </Link>
        {job.is_hidden && onUnhide && (
          <button
            onClick={() => onUnhide(job.id)}
            className="text-xs text-muted hover:text-green-600 transition-colors px-2 py-1 rounded hover:bg-green-50"
          >
            Unhide
          </button>
        )}
        {!job.is_hidden && onHide && (
          <button
            onClick={() => onHide(job.id)}
            className="text-xs text-muted hover:text-red-500 transition-colors px-2 py-1 rounded hover:bg-red-50"
          >
            Not interested
          </button>
        )}
      </div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/JobCard.tsx
git commit -m "feat(frontend): add unhide button to JobCard"
```

---

### Task 3: Frontend — JobList visibility filter

**Files:**
- Modify: `frontend/components/JobList.tsx`

- [ ] **Step 1: Add `visibility` state**

After the existing `sort` state declaration (line ~31), add:

```tsx
  const [visibility, setVisibility] = useState<"visible" | "hidden" | "all">(
    (searchParams.get("visibility") as "visible" | "hidden" | "all") ?? "visible"
  );
```

- [ ] **Step 2: Update `hasActiveFilters`**

Replace the existing `hasActiveFilters` line with:

```tsx
  const hasActiveFilters = !!(keyword || location || includeTags.length || excludeTags.length || isRepost !== "all" || sort !== "latest" || visibility !== "visible");
```

- [ ] **Step 3: Update `resetFilters`**

Add `setVisibility("visible");` inside the `resetFilters` callback:

```tsx
  const resetFilters = useCallback(() => {
    setKeyword("");
    setLocation("");
    setIncludeTags([]);
    setExcludeTags([]);
    setIsRepost("all");
    setSort("latest");
    setVisibility("visible");
  }, []);
```

- [ ] **Step 4: Update URL sync effect**

Add `visibility` to the URL params effect (after the `isRepost` block):

```tsx
    if (visibility !== "visible") params.set("visibility", visibility);
```

The full effect should be:

```tsx
  useEffect(() => {
    const params = new URLSearchParams();
    if (keyword) params.set("keyword", keyword);
    if (location) params.set("location", location);
    if (includeTags.length) params.set("include_tag", includeTags.join(","));
    if (excludeTags.length) params.set("exclude_tag", excludeTags.join(","));
    if (isRepost !== "all") params.set("is_repost", isRepost);
    if (visibility !== "visible") params.set("visibility", visibility);
    if (sort !== "latest") params.set("sort", sort);
    const qs = params.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [keyword, location, includeTags, excludeTags, isRepost, visibility, sort]);
```

- [ ] **Step 5: Update `buildParams`**

Add `visibility` to the `buildParams` callback:

```tsx
  const buildParams = useCallback((p: number) => {
    const params = new URLSearchParams({ sort, page: String(p), page_size: String(pageSize) });
    if (keyword) params.set("keyword", keyword);
    if (location) params.set("location", location);
    if (includeTags.length) params.set("include_tag", includeTags.join(","));
    if (excludeTags.length) params.set("exclude_tag", excludeTags.join(","));
    if (isRepost !== "all") params.set("is_repost", isRepost);
    if (visibility !== "visible") params.set("visibility", visibility);
    return params;
  }, [keyword, location, includeTags, excludeTags, isRepost, visibility, sort, pageSize]);
```

- [ ] **Step 6: Add `visibility` to page-reset deps**

Update the page-reset effect dependency array:

```tsx
  }, [keyword, location, includeTags, excludeTags, isRepost, visibility, sort, pageSize, refreshKey]);
```

- [ ] **Step 7: Add `onUnhide` handler**

After the existing `handleHide` function, add:

```tsx
  const handleUnhide = async (id: number) => {
    setData((prev) => ({ ...prev, items: prev.items.filter((j) => j.id !== id), total: prev.total - 1 }));
    await fetch(`${API}/api/jobs/${id}/unhide`, { method: "PATCH" });
  };
```

- [ ] **Step 8: Add the visibility select to the filter grid**

The current filter grid is a `grid-cols-4`. Change it to `grid-cols-5` and add the visibility select as the first item:

```tsx
        <div className="grid grid-cols-5 gap-3">
          <select
            value={visibility}
            onChange={(e) => setVisibility(e.target.value as "visible" | "hidden" | "all")}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
          >
            <option value="visible">Active jobs</option>
            <option value="hidden">Hidden jobs</option>
            <option value="all">All jobs</option>
          </select>
          <TagMultiSelect
            label="Include tags"
            tags={allTags}
            selected={includeTags}
            onChange={setIncludeTags}
          />
          <TagMultiSelect
            label="Exclude tags"
            tags={allTags}
            selected={excludeTags}
            onChange={setExcludeTags}
          />
          <select
            value={isRepost}
            onChange={(e) => setIsRepost(e.target.value as "all" | "originals" | "reposts")}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
          >
            <option value="all">All jobs</option>
            <option value="originals">Originals only</option>
            <option value="reposts">Reposts only</option>
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as "latest" | "oldest")}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
          >
            <option value="latest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>
```

- [ ] **Step 9: Pass `onUnhide` to `JobCard`**

Update the `JobCard` render call inside the grid:

```tsx
            <JobCard key={job.id} job={job} allTags={allTags} sponsors={sponsors} onHide={handleHide} onUnhide={handleUnhide} />
```

- [ ] **Step 10: Commit**

```bash
git add frontend/components/JobList.tsx
git commit -m "feat(frontend): add visibility filter with unhide support"
```
