# AI Batch Job Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manually-triggered batch LLM service that hides clearly irrelevant jobs, with a `hide_reason` field stored for both AI and user dismissals, surfaced on a dedicated `/ai-filter` page.

**Architecture:** An in-memory status dict (same pattern as the scraper) drives a background `asyncio` task that chunks visible jobs into batches of 20, makes one `litellm` call per batch, and writes `is_hidden=True` + `hide_reason=<AI reason>` for matches. Three new API endpoints expose run/status/cancel. The frontend adds a nav link, a dedicated page with progress UI, and a hide-reason label on `JobCard`.

**Tech Stack:** Python/FastAPI/SQLModel/litellm (backend), Next.js/TypeScript/Tailwind (frontend), SQLite via Alembic migration.

**Spec:** `docs/superpowers/specs/2026-07-30-ai-batch-filter-design.md`

---

## File Map

**Create:**
- `backend/alembic/versions/0009_add_hide_reason.py`
- `backend/ai_filter_service.py`
- `backend/routes/ai_filter.py`
- `backend/tests/test_ai_filter.py`
- `frontend/app/ai-filter/page.tsx`

**Modify:**
- `backend/models.py` — add `hide_reason` to `Job`
- `backend/schemas.py` — add `hide_reason` to `JobOut`; add `AiFilterStatus`
- `backend/routes/jobs.py` — set `hide_reason="USER"` in hide endpoint; pass `hide_reason` in `_to_out`
- `backend/main.py` — register `ai_filter` router
- `frontend/types.ts` — add `hide_reason` to `Job`; add `AiFilterStatus`
- `frontend/components/Nav.tsx` — add AI Filter nav link
- `frontend/components/JobCard.tsx` — show hide reason label

---

## Task 1: Add `hide_reason` to data model, schema, and migration

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/schemas.py`
- Modify: `backend/routes/jobs.py`
- Create: `backend/alembic/versions/0009_add_hide_reason.py`

- [ ] **Step 1: Add field to `Job` model**

In `backend/models.py`, add `hide_reason` to the `Job` class after `notes`:

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
    hide_reason: Optional[str] = None
    resume_version_id: Optional[int] = Field(default=None, foreign_key="resume_version.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Add `hide_reason` to `JobOut` schema**

In `backend/schemas.py`, add to `JobOut` after `notes`:

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
    hide_reason: Optional[str] = None
    status: str = "SAVED"
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Pass `hide_reason` in `_to_out`**

In `backend/routes/jobs.py`, update `_to_out` to include `hide_reason`:

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
        hide_reason=j.hide_reason,
        tags=_get_job_tags(session, j.id),
    )
```

- [ ] **Step 4: Create migration**

Create `backend/alembic/versions/0009_add_hide_reason.py`:

```python
"""add hide_reason to job

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-30
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in inspect(conn).get_columns("job")]
    if "hide_reason" not in cols:
        op.add_column("job", sa.Column("hide_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in inspect(conn).get_columns("job")]
    if "hide_reason" in cols:
        op.drop_column("job", "hide_reason")
```

- [ ] **Step 5: Write a failing test verifying `hide_reason` appears in GET /jobs/:id response**

Add to `backend/tests/test_api.py` (find the existing `TestClient` setup in that file and follow the same pattern). Add this test:

```python
def test_job_out_includes_hide_reason(client, session):
    # The existing test file likely has a `client` fixture or creates TestClient(app).
    # Follow the existing pattern. The key assertion is:
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    # Create a job directly in the DB
    from models import Job
    from database import engine
    from sqlmodel import Session
    with Session(engine) as s:
        job = Job(
            seek_url="/j/test-hide-reason",
            seek_urls="[]",
            title="Test Role",
            listed_dates="[]",
            hide_reason="Electrical engineer",
            is_hidden=True,
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        job_id = job.id

    r = client.get(f"/api/jobs/{job_id}")
    assert r.status_code == 200
    assert r.json()["hide_reason"] == "Electrical engineer"
```

- [ ] **Step 6: Run test — expect FAIL (field missing from response)**

```bash
cd backend && uv run pytest tests/test_api.py::test_job_out_includes_hide_reason -v
```

Expected: FAIL — `hide_reason` not in response or `KeyError`.

- [ ] **Step 7: Run migration against test DB then re-run test**

```bash
cd backend && DATABASE_URL=sqlite:///./data/test.db uv run alembic upgrade head
uv run pytest tests/test_api.py::test_job_out_includes_hide_reason -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/models.py backend/schemas.py backend/routes/jobs.py \
        backend/alembic/versions/0009_add_hide_reason.py \
        backend/tests/test_api.py
git commit -m "feat(db): add hide_reason field to job model and schema"
```

---

## Task 2: Set `hide_reason="USER"` when user hides a job

**Files:**
- Modify: `backend/routes/jobs.py` — `hide_job` endpoint

- [ ] **Step 1: Write a failing test**

Add to `backend/tests/test_api.py`:

```python
def test_hide_job_sets_user_reason():
    from fastapi.testclient import TestClient
    from main import app
    from models import Job
    from database import engine
    from sqlmodel import Session

    client = TestClient(app)

    with Session(engine) as s:
        job = Job(seek_url="/j/test-user-hide", seek_urls="[]", title="Some Role", listed_dates="[]")
        s.add(job)
        s.commit()
        s.refresh(job)
        job_id = job.id

    r = client.patch(f"/api/jobs/{job_id}/hide")
    assert r.status_code == 200
    data = r.json()
    assert data["is_hidden"] is True
    assert data["hide_reason"] == "USER"
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd backend && uv run pytest tests/test_api.py::test_hide_job_sets_user_reason -v
```

Expected: FAIL — `hide_reason` is `null`, not `"USER"`.

- [ ] **Step 3: Update `hide_job` endpoint**

In `backend/routes/jobs.py`, update `hide_job`:

```python
@router.patch("/jobs/{job_id}/hide", response_model=JobOut)
def hide_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_hidden = True
    job.hide_reason = "USER"
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd backend && uv run pytest tests/test_api.py::test_hide_job_sets_user_reason -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/jobs.py backend/tests/test_api.py
git commit -m "feat(jobs): set hide_reason=USER when user hides a job"
```

---

## Task 3: Add `AiFilterStatus` schema

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add schema**

In `backend/schemas.py`, append:

```python
class AiFilterStatus(BaseModel):
    status: str
    current_batch: int = 0
    total_batches: int = 0
    evaluated: int = 0
    hidden: int = 0
    error: Optional[str] = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/schemas.py
git commit -m "feat(schemas): add AiFilterStatus schema"
```

---

## Task 4: Create AI filter service

**Files:**
- Create: `backend/ai_filter_service.py`
- Create: `backend/tests/test_ai_filter.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_ai_filter.py`:

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch

from models import Job
from database import engine
from sqlmodel import Session

import ai_filter_service


def _make_job(seek_url: str, title: str, description: str = "", is_hidden: bool = False) -> Job:
    with Session(engine) as s:
        job = Job(
            seek_url=seek_url,
            seek_urls="[]",
            title=title,
            description=description,
            listed_dates="[]",
            is_hidden=is_hidden,
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        return job


def test_parse_response_plain_json():
    content = '[{"id": 1, "hide": true, "reason": "Civil engineer"}]'
    result = ai_filter_service._parse_response(content)
    assert result == [{"id": 1, "hide": True, "reason": "Civil engineer"}]


def test_parse_response_strips_markdown_fences():
    content = '```json\n[{"id": 2, "hide": false, "reason": ""}]\n```'
    result = ai_filter_service._parse_response(content)
    assert result == [{"id": 2, "hide": False, "reason": ""}]


def test_build_batch_payload_truncates_description():
    job = Job(id=99, seek_url="/j/x", title="Engineer", description="x" * 600)
    payload = ai_filter_service._build_batch_payload([job])
    assert len(payload[0]["description"]) == 500


def test_build_batch_payload_handles_none_description():
    job = Job(id=98, seek_url="/j/y", title="Dev", description=None)
    payload = ai_filter_service._build_batch_payload([job])
    assert payload[0]["description"] == ""


async def test_run_filter_hides_matching_job():
    job = _make_job("/j/civil-test", "Civil Engineer", "Build bridges and roads")

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([
        {"id": job.id, "hide": True, "reason": "Civil engineering role"}
    ])

    with patch("ai_filter_service.litellm.acompletion", new=AsyncMock(return_value=mock_resp)):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.is_hidden is True
        assert updated.hide_reason == "Civil engineering role"

    status = ai_filter_service.get_status()
    assert status["hidden"] >= 1
    assert status["status"] == "done"


async def test_run_filter_keeps_non_matching_job():
    job = _make_job("/j/python-dev", "Senior Python Developer", "FastAPI microservices")

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([
        {"id": job.id, "hide": False, "reason": ""}
    ])

    with patch("ai_filter_service.litellm.acompletion", new=AsyncMock(return_value=mock_resp)):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.is_hidden is False
        assert updated.hide_reason is None


async def test_run_filter_skips_already_hidden_jobs():
    job = _make_job("/j/already-hidden", "Electrical Engineer", "High voltage", is_hidden=True)

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([])

    with patch("ai_filter_service.litellm.acompletion", new=AsyncMock(return_value=mock_resp)) as mock_llm:
        await ai_filter_service.run_filter()

    # Already-hidden job should not appear in any batch sent to the LLM
    all_ids_sent = []
    for call in mock_llm.call_args_list:
        user_msg = call.kwargs["messages"][-1]["content"]
        batch = json.loads(user_msg)
        all_ids_sent.extend(item["id"] for item in batch)
    assert job.id not in all_ids_sent


async def test_run_filter_truncates_reason_to_60_chars():
    job = _make_job("/j/asp-net", "ASP.NET Developer", "ASP.NET MVC required")

    long_reason = "A" * 80
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([
        {"id": job.id, "hide": True, "reason": long_reason}
    ])

    with patch("ai_filter_service.litellm.acompletion", new=AsyncMock(return_value=mock_resp)):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.hide_reason is not None
        assert len(updated.hide_reason) <= 60


async def test_run_filter_continues_after_bad_json_batch():
    job1 = _make_job("/j/bad-json", "PM Construction", "Build roads")
    job2 = _make_job("/j/good-json", "VP Engineering", "Lead 50 engineers")

    call_count = 0

    async def mock_llm(**kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        if call_count == 1:
            mock_resp.choices[0].message.content = "NOT VALID JSON {{{"
        else:
            mock_resp.choices[0].message.content = json.dumps([
                {"id": job2.id, "hide": True, "reason": "Leadership role"}
            ])
        return mock_resp

    with patch("ai_filter_service.litellm.acompletion", new=mock_llm), \
         patch("ai_filter_service.BATCH_SIZE", 1):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated2 = s.get(Job, job2.id)
        assert updated2.is_hidden is True

    assert ai_filter_service.get_status()["status"] == "done"


async def test_run_filter_cancel():
    # Two jobs, BATCH_SIZE=1 so there are two batches.
    # After the first batch the mock sets cancel_requested so the second batch is skipped.
    _make_job("/j/cancel-a", "Software Engineer A", "Python")
    _make_job("/j/cancel-b", "Software Engineer B", "JavaScript")

    call_count = 0

    async def mock_llm(**kwargs):
        nonlocal call_count
        call_count += 1
        ai_filter_service._state["cancel_requested"] = True  # signal cancel after first batch
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps([])
        return mock_resp

    with patch("ai_filter_service.litellm.acompletion", new=mock_llm), \
         patch("ai_filter_service.BATCH_SIZE", 1):
        await ai_filter_service.run_filter()

    assert call_count == 1  # second batch never ran
    assert ai_filter_service.get_status()["status"] == "cancelled"
```

- [ ] **Step 2: Run tests — expect FAIL (module not found)**

```bash
cd backend && uv run pytest tests/test_ai_filter.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_filter_service'`.

- [ ] **Step 3: Create `backend/ai_filter_service.py`**

```python
import json
import logging
import litellm
from sqlmodel import Session, select

from ai_config import strip_html
from database import engine
from models import Job

logger = logging.getLogger(__name__)

BATCH_SIZE = 20
DEFAULT_MODEL = "gpt-4o-mini"

_state: dict = {
    "status": "idle",
    "current_batch": 0,
    "total_batches": 0,
    "evaluated": 0,
    "hidden": 0,
    "error": None,
    "cancel_requested": False,
}

_FILTER_SYSTEM = """\
You are filtering job listings for a software engineer seeking backend, frontend, or full-stack roles.

For each job, decide if it should be hidden because it clearly does not match.

Hide a job if ANY of these rules apply:
- Leadership-only role: Principal Engineer, Engineering Lead/Manager, VP/Director of Engineering
- Non-software PM: Project Manager or Product Manager for construction, infrastructure, civil, or non-tech domains
- Non-software engineering discipline: Electrical, Civil, Mechanical, or Structural Engineer
- Requires ASP.NET as a core or mandatory skill
- Clearly outside software/web/data/cloud engineering

If there is reasonable doubt, do NOT hide — only filter obvious mismatches.

Return ONLY a JSON array, no markdown, no other text. Each element must have exactly these keys:
{"id": <int>, "hide": <bool>, "reason": "<max 60 chars, empty string if hide is false>"}
"""


def get_status() -> dict:
    return {k: v for k, v in _state.items() if k != "cancel_requested"}


def _reset() -> None:
    _state.update({
        "status": "running",
        "current_batch": 0,
        "total_batches": 0,
        "evaluated": 0,
        "hidden": 0,
        "error": None,
        "cancel_requested": False,
    })


def _build_batch_payload(jobs: list[Job]) -> list[dict]:
    return [
        {"id": job.id, "title": job.title, "description": strip_html(job.description or "")[:500]}
        for job in jobs
    ]


def _parse_response(content: str) -> list[dict]:
    """Extract JSON array from LLM response, stripping any markdown fences."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]).strip()
    return json.loads(content)


async def run_filter(model: str = DEFAULT_MODEL) -> None:
    _reset()
    try:
        with Session(engine) as session:
            jobs = list(session.exec(select(Job).where(Job.is_hidden == False)).all())  # noqa: E712

        if not jobs:
            _state["status"] = "done"
            return

        batches = [jobs[i:i + BATCH_SIZE] for i in range(0, len(jobs), BATCH_SIZE)]
        _state["total_batches"] = len(batches)

        for batch_idx, batch in enumerate(batches):
            if _state["cancel_requested"]:
                _state["status"] = "cancelled"
                return

            _state["current_batch"] = batch_idx + 1
            payload = _build_batch_payload(batch)

            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=[
                        {"role": "system", "content": _FILTER_SYSTEM},
                        {"role": "user", "content": json.dumps(payload)},
                    ],
                )
                content = response.choices[0].message.content
            except Exception as exc:
                logger.error("Batch %d LLM call failed: %s", batch_idx + 1, exc)
                _state["status"] = "error"
                _state["error"] = str(exc)
                return

            try:
                decisions = _parse_response(content)
            except Exception as exc:
                logger.error("Batch %d JSON parse failed: %s", batch_idx + 1, exc)
                _state["evaluated"] += len(batch)
                continue

            hide_map = {d["id"]: d for d in decisions if d.get("hide")}

            with Session(engine) as session:
                for job in batch:
                    if job.id in hide_map:
                        db_job = session.get(Job, job.id)
                        if db_job:
                            db_job.is_hidden = True
                            db_job.hide_reason = hide_map[job.id].get("reason", "AI filtered")[:60]
                            session.add(db_job)
                            _state["hidden"] += 1
                session.commit()

            _state["evaluated"] += len(batch)

        _state["status"] = "done"

    except Exception as exc:
        logger.exception("AI filter failed: %s", exc)
        _state["status"] = "error"
        _state["error"] = str(exc)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd backend && uv run pytest tests/test_ai_filter.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/ai_filter_service.py backend/tests/test_ai_filter.py
git commit -m "feat: add AI batch filter service with LLM-based job filtering"
```

---

## Task 5: Create AI filter routes and register in `main.py`

**Files:**
- Create: `backend/routes/ai_filter.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing route tests**

Add to `backend/tests/test_ai_filter.py`:

```python
from fastapi.testclient import TestClient
from main import app
import ai_filter_service

_client = TestClient(app)


def test_filter_status_endpoint_returns_idle():
    ai_filter_service._state["status"] = "idle"
    r = _client.get("/api/ai-filter/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "idle"
    assert "current_batch" in data
    assert "total_batches" in data
    assert "evaluated" in data
    assert "hidden" in data


def test_filter_run_returns_409_when_running():
    ai_filter_service._state["status"] = "running"
    r = _client.post("/api/ai-filter/run")
    assert r.status_code == 409
    ai_filter_service._state["status"] = "idle"


def test_filter_cancel_sets_flag():
    ai_filter_service._state["cancel_requested"] = False
    r = _client.post("/api/ai-filter/cancel")
    assert r.status_code == 200
    assert ai_filter_service._state["cancel_requested"] is True
    ai_filter_service._state["cancel_requested"] = False
```

- [ ] **Step 2: Run tests — expect FAIL (404 on routes)**

```bash
cd backend && uv run pytest tests/test_ai_filter.py::test_filter_status_endpoint_returns_idle tests/test_ai_filter.py::test_filter_run_returns_409_when_running tests/test_ai_filter.py::test_filter_cancel_sets_flag -v
```

Expected: FAIL — 404 Not Found (routes don't exist yet).

- [ ] **Step 3: Create `backend/routes/ai_filter.py`**

```python
import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ai_filter_service import get_status, run_filter, _state
from schemas import AiFilterStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ai-filter/run", status_code=202)
async def trigger_filter(model: str = "gpt-4o-mini") -> dict:
    if _state["status"] == "running":
        return JSONResponse(status_code=409, content={"detail": "Filter already running"})
    asyncio.create_task(run_filter(model))
    return {"status": "started"}


@router.get("/ai-filter/status", response_model=AiFilterStatus)
def get_filter_status() -> AiFilterStatus:
    return AiFilterStatus(**get_status())


@router.post("/ai-filter/cancel")
def cancel_filter() -> dict:
    _state["cancel_requested"] = True
    return {"status": "cancel_requested"}
```

- [ ] **Step 4: Register router in `backend/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db
from routes import jobs, scrape, tags, sponsors
from routes.resume import router as resume_router, seed_resume
from routes.ai import router as ai_router
from routes.ai_filter import router as ai_filter_router
import os
import logging

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    seed_resume()
    yield


app = FastAPI(title="Aus Job Scraper", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(sponsors.router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(ai_filter_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run route tests — expect PASS**

```bash
cd backend && uv run pytest tests/test_ai_filter.py::test_filter_status_endpoint_returns_idle tests/test_ai_filter.py::test_filter_run_returns_409_when_running tests/test_ai_filter.py::test_filter_cancel_sets_flag -v
```

Expected: All PASS.

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
cd backend && uv run pytest tests/ -v --ignore=tests/test_integration.py
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/routes/ai_filter.py backend/main.py
git commit -m "feat(api): add AI filter run/status/cancel endpoints"
```

---

## Task 6: Update frontend types

**Files:**
- Modify: `frontend/types.ts`

- [ ] **Step 1: Add `hide_reason` to `Job` and add `AiFilterStatus`**

Replace the contents of `frontend/types.ts` with:

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
  hide_reason: string | null;
  tags: Tag[];
  resume_version_id: number | null;
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

export interface AiFilterStatus {
  status: string;
  current_batch: number;
  total_batches: number;
  evaluated: number;
  hidden: number;
  error: string | null;
}

export interface ModelInfo {
  id: string;
  label: string;
}

export interface MessageOut {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface CoverLetterOut {
  id: number;
  job_id: number;
  resume_version_id: number;
  content: string;
  conversation_id: number;
  messages: MessageOut[];
  updated_at: string;
}

export interface AdvisorOut {
  conversation_id: number;
  messages: MessageOut[];
}

export interface ResumeVersionMeta {
  id: number;
  label: string;
  created_at: string;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/types.ts
git commit -m "feat(types): add hide_reason to Job and add AiFilterStatus"
```

---

## Task 7: Add AI Filter link to Nav

**Files:**
- Modify: `frontend/components/Nav.tsx`

- [ ] **Step 1: Add nav link**

In `frontend/components/Nav.tsx`, add `{ href: "/ai-filter", label: "AI Filter" }` to the links array:

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Nav() {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" || pathname.startsWith("/jobs") : pathname === href;

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-3xl mx-auto px-4 flex items-center justify-between h-14">
        <span className="text-navy font-bold text-lg">Aus Job Scraper</span>
        <div className="flex gap-1">
          {[
            { href: "/", label: "Job Listings" },
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
git commit -m "feat(nav): add AI Filter link"
```

---

## Task 8: Show `hide_reason` label in `JobCard`

**Files:**
- Modify: `frontend/components/JobCard.tsx`

- [ ] **Step 1: Add hide reason label beneath company name**

In `frontend/components/JobCard.tsx`, add the hide reason label inside the title section, after the company `<p>` block. The relevant section becomes:

```tsx
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
  {job.is_hidden && job.hide_reason && (
    <p className="text-xs text-muted mt-0.5">
      {job.hide_reason === "USER"
        ? "Hidden by: You"
        : `Hidden by: AI — ${job.hide_reason}`}
    </p>
  )}
</div>
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/JobCard.tsx
git commit -m "feat(ui): show hide_reason label on hidden jobs in JobCard"
```

---

## Task 9: Create AI Filter page

**Files:**
- Create: `frontend/app/ai-filter/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/app/ai-filter/page.tsx`:

```tsx
"use client";
import { useEffect, useRef, useState } from "react";
import { AiFilterStatus } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AiFilterPage() {
  const [filterStatus, setFilterStatus] = useState<AiFilterStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = async (): Promise<AiFilterStatus> => {
    const r = await fetch(`${API}/api/ai-filter/status`);
    const data: AiFilterStatus = await r.json();
    setFilterStatus(data);
    return data;
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = () => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const data = await fetchStatus();
      if (data.status !== "running") stopPolling();
    }, 1500);
  };

  useEffect(() => {
    fetchStatus().then((data) => {
      if (data.status === "running") startPolling();
    });
    return () => stopPolling();
  }, []);

  const handleRun = async () => {
    await fetch(`${API}/api/ai-filter/run`, { method: "POST" });
    await fetchStatus();
    startPolling();
  };

  const handleCancel = async () => {
    await fetch(`${API}/api/ai-filter/cancel`, { method: "POST" });
  };

  const isRunning = filterStatus?.status === "running";
  const progress =
    filterStatus && filterStatus.total_batches > 0
      ? Math.round((filterStatus.current_batch / filterStatus.total_batches) * 100)
      : 0;

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <div className="h-1 w-12 bg-accent rounded mb-6" />
      <h1 className="text-2xl font-bold text-navy mb-2">AI Job Filter</h1>
      <p className="text-sm text-muted mb-8">
        Automatically hides jobs that clearly do not match a software engineering role — e.g. civil
        engineers, ASP.NET-only roles, and leadership positions.
      </p>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-5">
        <div className="flex items-center gap-3">
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="bg-secondary text-white text-sm font-semibold px-4 py-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRunning ? "Running..." : "Run Filter"}
          </button>
          {isRunning && (
            <button
              onClick={handleCancel}
              className="text-sm text-muted hover:text-red-500 transition-colors px-3 py-2 rounded-lg hover:bg-red-50"
            >
              Cancel
            </button>
          )}
        </div>

        {filterStatus && filterStatus.status !== "idle" && (
          <div className="space-y-3">
            {isRunning && filterStatus.total_batches > 0 && (
              <div>
                <div className="flex justify-between text-xs text-muted mb-1.5">
                  <span>
                    Batch {filterStatus.current_batch} / {filterStatus.total_batches}
                  </span>
                  <span>
                    {filterStatus.evaluated} evaluated &mdash; {filterStatus.hidden} hidden
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            {filterStatus.status === "done" && (
              <p className="text-sm text-gray-700">
                Done &mdash;{" "}
                <span className="font-semibold text-navy">{filterStatus.hidden}</span> jobs hidden
                out of{" "}
                <span className="font-semibold text-navy">{filterStatus.evaluated}</span> evaluated.
              </p>
            )}

            {filterStatus.status === "cancelled" && (
              <p className="text-sm text-muted">
                Cancelled &mdash; {filterStatus.hidden} jobs hidden before cancellation.
              </p>
            )}

            {filterStatus.status === "error" && (
              <p className="text-sm text-red-500">Error: {filterStatus.error}</p>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Run full backend test suite one more time**

```bash
cd backend && uv run pytest tests/ -v --ignore=tests/test_integration.py
```

Expected: All tests PASS.

- [ ] **Step 4: Final commit**

```bash
git add frontend/app/ai-filter/page.tsx
git commit -m "feat(ui): add AI Filter page with run/progress/cancel UI"
```

---

## Completion Checklist

- [ ] Migration `0009_add_hide_reason.py` applied to production DB on deploy (`alembic upgrade head`)
- [ ] `hide_reason` appears in `GET /api/jobs/:id` response
- [ ] `PATCH /api/jobs/:id/hide` sets `hide_reason="USER"`
- [ ] `POST /api/ai-filter/run` starts background task, returns 409 if already running
- [ ] `GET /api/ai-filter/status` returns live progress
- [ ] `POST /api/ai-filter/cancel` stops the run
- [ ] AI Filter page accessible from nav, shows progress, cancel, and result summary
- [ ] Hidden jobs show `hide_reason` label in `JobCard` when viewing hidden jobs
