# Filter Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add repost status filter (All / Originals / Reposts) and combined tag filter (include + exclude) to the job list.

**Architecture:** Rename existing `tag` query param to `include_tag`, add `exclude_tag` (NOT EXISTS subquery) and `is_repost` (WHERE clause) params on `GET /api/jobs`. Frontend adds two new `<select>` controls in `JobList.tsx`.

**Tech Stack:** Python/FastAPI/SQLModel (backend), Next.js/TypeScript/Tailwind (frontend), pytest (tests), uv (package manager)

---

## File Map

| File | Change |
|---|---|
| `backend/routes/jobs.py` | Rename `tag` → `include_tag`, add `exclude_tag` + `is_repost` |
| `backend/tests/test_tag_filter.py` | Rename `tag=` → `include_tag=`, add exclude/combined tests |
| `backend/tests/test_repost_filter.py` | New file — tests for `is_repost` param |
| `frontend/components/JobList.tsx` | Add `excludeTag` + `isRepost` state and two new selects |

---

### Task 1: Rename `tag` → `include_tag` in backend and tests

**Files:**
- Modify: `backend/routes/jobs.py`
- Modify: `backend/tests/test_tag_filter.py`

- [ ] **Step 1: Update all `tag=` usages in test_tag_filter.py to `include_tag=`**

Replace every occurrence of `?tag=` with `?include_tag=` and `&tag=` with `&include_tag=` in `backend/tests/test_tag_filter.py`:

```python
# test_filter_by_tag_returns_matching_jobs
resp = client.get("/api/jobs?include_tag=Interested")

# test_filter_by_tag_excludes_untagged_jobs
resp = client.get("/api/jobs?include_tag=Python")

# test_filter_by_tag_case_insensitive
resp = client.get("/api/jobs?include_tag=interested")

# test_filter_by_unknown_tag_returns_empty
resp = client.get("/api/jobs?include_tag=nonexistent")

# test_filter_by_tag_combined_with_keyword
resp = client.get("/api/jobs?include_tag=Python&keyword=senior")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && uv run pytest tests/test_tag_filter.py -v
```

Expected: all 5 tests FAIL (backend still uses `tag=`, so include_tag is ignored and all jobs return)

- [ ] **Step 3: Rename `tag` param to `include_tag` in `backend/routes/jobs.py`**

Replace the function signature and filter block:

```python
@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    include_tag: Optional[str] = Query(None),
    sort: Literal["latest", "oldest"] = Query("latest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
):
    query = select(Job).where(Job.is_hidden == False)  # noqa: E712

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

    if include_tag:
        query = query.join(JobTag, Job.id == JobTag.job_id).join(Tag, JobTag.tag_id == Tag.id).where(Tag.name.ilike(include_tag))

    total = session.exec(select(func.count()).select_from(query.subquery())).one()

    order = col(Job.latest_listing_date).desc() if sort == "latest" else col(Job.latest_listing_date).asc()
    jobs = session.exec(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()

    return JobsPage(items=[_to_out(j, session) for j in jobs], total=total, page=page, page_size=page_size)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend && uv run pytest tests/test_tag_filter.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/jobs.py backend/tests/test_tag_filter.py
git commit -m "refactor(api): rename tag param to include_tag"
```

---

### Task 2: Add `exclude_tag` backend support

**Files:**
- Modify: `backend/routes/jobs.py`
- Modify: `backend/tests/test_tag_filter.py`

- [ ] **Step 1a: Update `make_job` in `test_tag_filter.py` to accept `is_repost`**

Replace the existing `make_job` function (around line 19) with:

```python
def make_job(seek_url, title="Dev", is_repost=False) -> int:
    with Session(engine) as s:
        job = Job(
            seek_url=seek_url,
            title=title,
            listed_dates=json.dumps(["2026-05-26"]),
            latest_listing_date="2026-05-26",
            is_repost=is_repost,
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        return job.id
```

- [ ] **Step 1b: Append two new `exclude_tag` tests to `test_tag_filter.py`**

```python
def test_exclude_tag_removes_tagged_jobs():
    job1 = make_job("https://seek.com.au/job/1")
    job2 = make_job("https://seek.com.au/job/2")
    tag_id = make_tag("Rejected")
    client.post(f"/api/jobs/{job2}/tags/{tag_id}")

    resp = client.get("/api/jobs?exclude_tag=Rejected")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert job1 in ids
    assert job2 not in ids


def test_include_and_exclude_tag_combined():
    job1 = make_job("https://seek.com.au/job/1")  # Python only
    job2 = make_job("https://seek.com.au/job/2")  # Python + Rejected
    job3 = make_job("https://seek.com.au/job/3")  # no tags

    python_id = make_tag("Python")
    rejected_id = make_tag("Rejected")
    client.post(f"/api/jobs/{job1}/tags/{python_id}")
    client.post(f"/api/jobs/{job2}/tags/{python_id}")
    client.post(f"/api/jobs/{job2}/tags/{rejected_id}")

    resp = client.get("/api/jobs?include_tag=Python&exclude_tag=Rejected")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}
```

- [ ] **Step 2: Run tests to confirm new tests fail**

```bash
cd backend && uv run pytest tests/test_tag_filter.py::test_exclude_tag_removes_tagged_jobs tests/test_tag_filter.py::test_include_and_exclude_tag_combined -v
```

Expected: both FAIL (exclude_tag param not implemented yet)

- [ ] **Step 3: Add `exclude_tag` param and NOT EXISTS logic to `backend/routes/jobs.py`**

Add the import at the top of the file (alongside existing imports):

```python
from sqlalchemy import exists as sa_exists
```

Update the function signature and add the filter block after the `include_tag` block:

```python
@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    include_tag: Optional[str] = Query(None),
    exclude_tag: Optional[str] = Query(None),
    sort: Literal["latest", "oldest"] = Query("latest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
):
    ...
    if include_tag:
        query = query.join(JobTag, Job.id == JobTag.job_id).join(Tag, JobTag.tag_id == Tag.id).where(Tag.name.ilike(include_tag))

    if exclude_tag:
        exc = f"%{exclude_tag}%"
        exclude_subq = (
            select(JobTag)
            .join(Tag, JobTag.tag_id == Tag.id)
            .where(JobTag.job_id == Job.id)
            .where(Tag.name.ilike(exc))
        ).exists()
        query = query.where(~exclude_subq)
    ...
```

- [ ] **Step 4: Run all tag filter tests**

```bash
cd backend && uv run pytest tests/test_tag_filter.py -v
```

Expected: all 7 tests PASS (5 original + 2 new exclude_tag tests)

- [ ] **Step 5: Commit**

```bash
git add backend/routes/jobs.py backend/tests/test_tag_filter.py
git commit -m "feat(api): add exclude_tag filter param"
```

---

### Task 3: Add `is_repost` backend support

**Files:**
- Modify: `backend/routes/jobs.py`
- Create: `backend/tests/test_repost_filter.py`

- [ ] **Step 1: Create `backend/tests/test_repost_filter.py` with failing tests**

```python
import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import engine
from models import Job

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def make_job(seek_url: str, is_repost: bool = False) -> int:
    with Session(engine) as s:
        job = Job(
            seek_url=seek_url,
            title="Dev",
            listed_dates=json.dumps(["2026-05-26"]),
            latest_listing_date="2026-05-26",
            is_repost=is_repost,
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        return job.id


def test_is_repost_default_returns_all_jobs():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_is_repost_all_returns_all_jobs():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=all")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_is_repost_originals_returns_only_non_reposts():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=originals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["is_repost"] is False


def test_is_repost_reposts_returns_only_reposts():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=reposts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["is_repost"] is True


def test_is_repost_invalid_value_returns_422():
    resp = client.get("/api/jobs?is_repost=maybe")
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && uv run pytest tests/test_repost_filter.py -v
```

Expected: `test_is_repost_default_returns_all_jobs` and `test_is_repost_all_returns_all_jobs` PASS (default behaviour), `test_is_repost_originals_*` and `test_is_repost_reposts_*` FAIL, `test_is_repost_invalid_value_returns_422` FAIL

- [ ] **Step 3: Add `is_repost` param to `backend/routes/jobs.py`**

Update the function signature and add the filter block after `exclude_tag`:

```python
@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    include_tag: Optional[str] = Query(None),
    exclude_tag: Optional[str] = Query(None),
    is_repost: Literal["all", "originals", "reposts"] = Query("all"),
    sort: Literal["latest", "oldest"] = Query("latest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
):
    query = select(Job).where(Job.is_hidden == False)  # noqa: E712

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

    if include_tag:
        query = query.join(JobTag, Job.id == JobTag.job_id).join(Tag, JobTag.tag_id == Tag.id).where(Tag.name.ilike(include_tag))

    if exclude_tag:
        exc = f"%{exclude_tag}%"
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
```

- [ ] **Step 4: Append cross-filter combined test to `test_tag_filter.py`**

```python
def test_include_tag_and_is_repost_combined():
    job1 = make_job("https://seek.com.au/job/1", is_repost=False)
    job2 = make_job("https://seek.com.au/job/2", is_repost=True)
    tag_id = make_tag("Python")
    client.post(f"/api/jobs/{job1}/tags/{tag_id}")
    client.post(f"/api/jobs/{job2}/tags/{tag_id}")

    resp = client.get("/api/jobs?include_tag=Python&is_repost=originals")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}
```

- [ ] **Step 5: Run all backend tests**

```bash
cd backend && uv run pytest tests/test_repost_filter.py tests/test_tag_filter.py -v
```

Expected: all 13 tests PASS (7 tag filter + 1 combined + 5 repost filter)

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
cd backend && uv run pytest -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/routes/jobs.py backend/tests/test_repost_filter.py backend/tests/test_tag_filter.py
git commit -m "feat(api): add is_repost filter param"
```

---

### Task 4: Update frontend — add exclude tag and repost selects

**Files:**
- Modify: `frontend/components/JobList.tsx`

- [ ] **Step 1: Update state and fetch logic in `JobList.tsx`**

Replace the `tag` state with `includeTag` and add `excludeTag` + `isRepost` states. Update `fetchJobs` to send the new params. The full updated section (lines 13–44):

```typescript
export default function JobList({ refreshKey }: Props) {
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [includeTag, setIncludeTag] = useState("");
  const [excludeTag, setExcludeTag] = useState("");
  const [isRepost, setIsRepost] = useState<"all" | "originals" | "reposts">("all");
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [sort, setSort] = useState<"latest" | "oldest">("latest");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [data, setData] = useState<JobsPage>({ items: [], total: 0, page: 1, page_size: 25 });

  useEffect(() => {
    fetch(`${API}/api/tags`).then((r) => r.json()).then(setAllTags);
  }, []);

  const fetchJobs = useCallback(async (p: number) => {
    const params = new URLSearchParams({ sort, page: String(p), page_size: String(pageSize) });
    if (keyword) params.set("keyword", keyword);
    if (location) params.set("location", location);
    if (includeTag) params.set("include_tag", includeTag);
    if (excludeTag) params.set("exclude_tag", excludeTag);
    if (isRepost !== "all") params.set("is_repost", isRepost);
    const res = await fetch(`${API}/api/jobs?${params}`);
    if (res.ok) setData(await res.json());
  }, [keyword, location, includeTag, excludeTag, isRepost, sort, pageSize]);

  useEffect(() => {
    setPage(1);
    fetchJobs(1);
  }, [keyword, location, includeTag, excludeTag, isRepost, sort, pageSize, refreshKey, fetchJobs]);
```

- [ ] **Step 2: Update the filter bar JSX in `JobList.tsx`**

Replace the existing filter bar `<div>` (lines 52–87) with:

```tsx
<div className="flex flex-col sm:flex-row gap-3 mb-4">
  <input
    type="text"
    placeholder="Filter by keyword..."
    value={keyword}
    onChange={(e) => setKeyword(e.target.value)}
    className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
  />
  <input
    type="text"
    placeholder="Filter by location..."
    value={location}
    onChange={(e) => setLocation(e.target.value)}
    className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
  />
  <select
    value={includeTag}
    onChange={(e) => setIncludeTag(e.target.value)}
    className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
  >
    <option value="">Include tag</option>
    {allTags.map((t) => (
      <option key={t.id} value={t.name}>{t.name}</option>
    ))}
  </select>
  <select
    value={excludeTag}
    onChange={(e) => setExcludeTag(e.target.value)}
    className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
  >
    <option value="">Exclude tag</option>
    {allTags.map((t) => (
      <option key={t.id} value={t.name}>{t.name}</option>
    ))}
  </select>
  <select
    value={isRepost}
    onChange={(e) => setIsRepost(e.target.value as "all" | "originals" | "reposts")}
    className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
  >
    <option value="all">All jobs</option>
    <option value="originals">Originals only</option>
    <option value="reposts">Reposts only</option>
  </select>
  <select
    value={sort}
    onChange={(e) => setSort(e.target.value as "latest" | "oldest")}
    className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
  >
    <option value="latest">Newest first</option>
    <option value="oldest">Oldest first</option>
  </select>
</div>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds with no type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/components/JobList.tsx
git commit -m "feat(ui): add exclude tag and repost status filters"
```
