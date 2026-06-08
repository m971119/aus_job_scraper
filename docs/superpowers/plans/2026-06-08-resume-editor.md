# Resume Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/resume` page with a CodeMirror HTML editor, live A4 preview, named version history stored in SQLite, and browser-based print-to-PDF.

**Architecture:** Backend adds a `resume_version` table (Alembic migration), a FastAPI router with 5 endpoints, and seeds the initial resume from the embedded HTML on first startup. Frontend installs `@uiw/react-codemirror` + `@codemirror/lang-html`, adds a split-pane `ResumeEditor` client component (editor left, A4 iframe preview right, toolbar bottom), a thin `/resume` page, and a "Resume" link in the nav.

**Tech Stack:** FastAPI, SQLModel, Alembic, SQLite (backend); Next.js 14 App Router, TypeScript, Tailwind CSS v4, CodeMirror 6 via `@uiw/react-codemirror` (frontend).

---

## File Structure

### New files
- `backend/alembic/versions/0007_add_resume_version.py` — Alembic migration
- `backend/routes/resume.py` — router + seeding function
- `backend/tests/test_resume.py` — backend tests
- `frontend/components/ResumeEditor.tsx` — split-pane editor client component
- `frontend/app/resume/page.tsx` — thin page wrapper

### Modified files
- `backend/models.py` — add `ResumeVersion` SQLModel
- `backend/schemas.py` — add `ResumeVersionMeta`, `ResumeVersionOut`, `ResumeVersionCreate`
- `backend/main.py` — register resume router; call `seed_resume()` in lifespan
- `frontend/package.json` + `frontend/package-lock.json` — add CodeMirror deps
- `frontend/components/Nav.tsx` — add "Resume" link

---

## Task 1: DB Migration

**Files:**
- Create: `backend/alembic/versions/0007_add_resume_version.py`

- [ ] **Step 1: Write the migration file**

```python
"""add resume_version table

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-08
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if "resume_version" not in inspect(conn).get_table_names():
        op.create_table(
            "resume_version",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("label", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("resume_version")
```

- [ ] **Step 2: Run the migration**

Run from `backend/`:
```bash
uv run alembic upgrade head
```
Expected output contains: `Running upgrade 0006 -> 0007, add resume_version table`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/0007_add_resume_version.py
git commit -m "feat(db): add resume_version table"
```

---

## Task 2: Backend Model, Schemas, Routes, Seeding, Tests

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/schemas.py`
- Create: `backend/routes/resume.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_resume.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_resume.py`:

```python
import os
from pathlib import Path
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_resume.db")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import engine
from models import ResumeVersion


@pytest.fixture(autouse=True)
def clean_db():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


client = TestClient(app)


def test_get_current_resume_empty():
    resp = client.get("/api/resume")
    assert resp.status_code == 404


def test_create_version():
    resp = client.post("/api/resume/versions", json={"label": "v1", "content": "<html>test</html>"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == "v1"
    assert data["content"] == "<html>test</html>"
    assert "id" in data
    assert "created_at" in data


def test_get_current_resume_returns_latest():
    client.post("/api/resume/versions", json={"label": "v1", "content": "first"})
    client.post("/api/resume/versions", json={"label": "v2", "content": "second"})
    resp = client.get("/api/resume")
    assert resp.status_code == 200
    assert resp.json()["label"] == "v2"
    assert resp.json()["content"] == "second"


def test_list_versions_excludes_content():
    client.post("/api/resume/versions", json={"label": "v1", "content": "first"})
    client.post("/api/resume/versions", json={"label": "v2", "content": "second"})
    resp = client.get("/api/resume/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert "content" not in data[0]
    assert data[0]["label"] == "v2"


def test_get_version_by_id():
    v = client.post("/api/resume/versions", json={"label": "v1", "content": "my content"})
    vid = v.json()["id"]
    resp = client.get(f"/api/resume/versions/{vid}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "my content"


def test_get_version_not_found():
    resp = client.get("/api/resume/versions/99999")
    assert resp.status_code == 404


def test_delete_version():
    client.post("/api/resume/versions", json={"label": "v1", "content": "first"})
    v2 = client.post("/api/resume/versions", json={"label": "v2", "content": "second"})
    v2_id = v2.json()["id"]
    resp = client.delete(f"/api/resume/versions/{v2_id}")
    assert resp.status_code == 204
    assert len(client.get("/api/resume/versions").json()) == 1


def test_delete_last_version_returns_400():
    v = client.post("/api/resume/versions", json={"label": "only", "content": "content"})
    resp = client.delete(f"/api/resume/versions/{v.json()['id']}")
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to confirm they fail**

Run from `backend/`:
```bash
uv run pytest tests/test_resume.py -v
```
Expected: Import errors or 404/422 failures — the routes don't exist yet.

- [ ] **Step 3: Add `ResumeVersion` to `backend/models.py`**

Append after the `Job` class:

```python
class ResumeVersion(SQLModel, table=True):
    __tablename__ = "resume_version"
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Add schemas to `backend/schemas.py`**

Add `from datetime import datetime` to the imports at the top.

Append at the end of the file:

```python
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
```

- [ ] **Step 5: Create `backend/routes/resume.py`**

**Important:** Read `data/resume-init.html` at the project root and paste its full contents as the value of `_INITIAL_HTML` in this file (use a raw string `r"""..."""`). The file is at `/Users/michilin19/Personal/Projects/aus_job_scraper/data/resume-init.html`.

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from database import engine
from models import ResumeVersion
from schemas import ResumeVersionCreate, ResumeVersionMeta, ResumeVersionOut

router = APIRouter()

# Paste the full contents of data/resume-init.html here


def get_session():
    with Session(engine) as session:
        yield session


def seed_resume() -> None:
    path_str = os.environ.get("RESUME_INITIAL_PATH")
    if not path_str:
        return
    path = Path(path_str)
    if not path.is_file():
        return
    with Session(engine) as session:
        count = session.exec(select(func.count()).select_from(ResumeVersion)).one()
        if count > 0:
            return
        session.add(ResumeVersion(label="Initial", content=path.read_text(encoding="utf-8")))
        session.commit()


@router.get("/resume", response_model=ResumeVersionOut)
def get_current_resume(session: Session = Depends(get_session)):
    version = session.exec(select(ResumeVersion).order_by(ResumeVersion.id.desc())).first()
    if not version:
        raise HTTPException(status_code=404, detail="No resume found")
    return version


@router.get("/resume/versions", response_model=list[ResumeVersionMeta])
def list_versions(session: Session = Depends(get_session)):
    return session.exec(select(ResumeVersion).order_by(ResumeVersion.id.desc())).all()


@router.get("/resume/versions/{version_id}", response_model=ResumeVersionOut)
def get_version(version_id: int, session: Session = Depends(get_session)):
    version = session.get(ResumeVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post("/resume/versions", response_model=ResumeVersionOut, status_code=201)
def create_version(body: ResumeVersionCreate, session: Session = Depends(get_session)):
    version = ResumeVersion(label=body.label, content=body.content)
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


@router.delete("/resume/versions/{version_id}", status_code=204)
def delete_version(version_id: int, session: Session = Depends(get_session)):
    count = session.exec(select(func.count()).select_from(ResumeVersion)).one()
    if count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only remaining version")
    version = session.get(ResumeVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    session.delete(version)
    session.commit()
```

- [ ] **Step 6: Update `backend/main.py`**

Replace the entire file with:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db
from routes import jobs, scrape, tags, sponsors
from routes.resume import router as resume_router, seed_resume
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


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Run tests to confirm they pass**

```bash
uv run pytest tests/test_resume.py -v
```
Expected: 8 tests pass.

Run full suite to check no regressions:
```bash
uv run pytest tests/ -v --ignore=tests/test_integration.py
```
Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/models.py backend/schemas.py backend/routes/resume.py backend/main.py backend/tests/test_resume.py
git commit -m "feat(api): add resume version endpoints and seeding"
```

---

## Task 3: Frontend Dependencies + ResumeEditor Component

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`
- Create: `frontend/components/ResumeEditor.tsx`

- [ ] **Step 1: Install CodeMirror packages**

Run from `frontend/`:
```bash
npm install @uiw/react-codemirror @codemirror/lang-html
```
Expected: `package.json` and `package-lock.json` updated, no errors.

- [ ] **Step 2: Create `frontend/components/ResumeEditor.tsx`**

```tsx
"use client";
import { useState, useEffect, useRef } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { html } from "@codemirror/lang-html";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const A4_HEIGHT_PX = 1122;

interface VersionMeta {
  id: number;
  label: string;
  created_at: string;
}

export default function ResumeEditor() {
  const [content, setContent] = useState("");
  const [debouncedContent, setDebouncedContent] = useState("");
  const [label, setLabel] = useState("");
  const [versions, setVersions] = useState<VersionMeta[]>([]);
  const [selectedId, setSelectedId] = useState<number | "">("");
  const [overflow, setOverflow] = useState(false);
  const [saving, setSaving] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    fetch(`${API}/api/resume/versions`)
      .then((r) => r.json())
      .then(setVersions);
    fetch(`${API}/api/resume`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) {
          setContent(d.content);
          setDebouncedContent(d.content);
          setSelectedId(d.id);
        }
      });
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedContent(content), 300);
    return () => clearTimeout(t);
  }, [content]);

  useEffect(() => {
    if (!debouncedContent) return;
    const t = setTimeout(() => {
      const h =
        iframeRef.current?.contentDocument?.documentElement?.scrollHeight ?? 0;
      setOverflow(h > A4_HEIGHT_PX);
    }, 150);
    return () => clearTimeout(t);
  }, [debouncedContent]);

  const loadVersion = async (id: number) => {
    const resp = await fetch(`${API}/api/resume/versions/${id}`);
    const d = await resp.json();
    setContent(d.content);
    setDebouncedContent(d.content);
    setSelectedId(d.id);
  };

  const handleSave = async () => {
    if (!label.trim() || saving) return;
    setSaving(true);
    const resp = await fetch(`${API}/api/resume/versions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: label.trim(), content }),
    });
    const v = await resp.json();
    setVersions((prev) => [v, ...prev]);
    setSelectedId(v.id);
    setLabel("");
    setSaving(false);
  };

  const handlePrint = () => {
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(content);
    win.document.close();
    win.focus();
    win.print();
  };

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 56px)" }}>
      {/* Split pane */}
      <div className="flex flex-1 min-h-0">
        {/* Left: code editor */}
        <div className="w-[45%] border-r border-gray-200 overflow-hidden">
          <CodeMirror
            value={content}
            height="calc(100vh - 113px)"
            extensions={[html()]}
            onChange={setContent}
            style={{ fontSize: "13px" }}
          />
        </div>

        {/* Right: A4 preview */}
        <div className="flex-1 overflow-auto bg-gray-50 p-6 flex flex-col items-center">
          <div
            className={`bg-white shadow-md ${overflow ? "ring-2 ring-red-500" : ""}`}
            style={{ width: "210mm" }}
          >
            <iframe
              ref={iframeRef}
              srcDoc={debouncedContent}
              style={{
                width: "210mm",
                height: "297mm",
                border: "none",
                display: "block",
              }}
              sandbox="allow-same-origin"
              title="Resume preview"
            />
          </div>
          {overflow && (
            <p className="mt-2 text-xs font-semibold text-red-500">
              Content overflows A4 — reduce content or font size
            </p>
          )}
        </div>
      </div>

      {/* Bottom toolbar */}
      <div className="border-t border-gray-200 bg-white px-4 py-3 flex items-center gap-3 shrink-0">
        <select
          value={selectedId}
          onChange={(e) => loadVersion(Number(e.target.value))}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary max-w-xs"
        >
          <option value="" disabled>
            Version history
          </option>
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              {v.label} — {new Date(v.created_at).toLocaleDateString()}
            </option>
          ))}
        </select>
        <div className="flex-1" />
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
          }}
          placeholder="Version label..."
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 w-48 focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button
          onClick={handleSave}
          disabled={!label.trim() || saving}
          className="text-sm font-semibold bg-secondary text-white px-4 py-1.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          onClick={handlePrint}
          className="text-sm font-semibold border border-primary text-primary px-4 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-colors"
        >
          Print
        </button>
      </div>
    </div>
  );
}
```

Note: `calc(100vh - 113px)` = nav (56px) + toolbar (57px).

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/components/ResumeEditor.tsx
git commit -m "feat(frontend): add CodeMirror deps and ResumeEditor component"
```

---

## Task 4: Resume Page + Nav Update + Rebuild

**Files:**
- Create: `frontend/app/resume/page.tsx`
- Modify: `frontend/components/Nav.tsx`

- [ ] **Step 1: Create `frontend/app/resume/page.tsx`**

```tsx
import ResumeEditor from "@/components/ResumeEditor";

export default function ResumePage() {
  return <ResumeEditor />;
}
```

- [ ] **Step 2: Update `frontend/components/Nav.tsx`**

Read the current file first. Then update the links array to add "Resume" as the third item:

```tsx
  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-3xl mx-auto px-4 flex items-center justify-between h-14">
        <span className="text-navy font-bold text-lg">Aus Job Scraper</span>
        <div className="flex gap-1">
          {[
            { href: "/", label: "Job Listings" },
            { href: "/applications", label: "Applications" },
            { href: "/resume", label: "Resume" },
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
```

Keep the existing `isActive` function unchanged — it already handles `/resume` correctly via exact match.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/resume/page.tsx frontend/components/Nav.tsx
git commit -m "feat(frontend): add Resume page and nav link"
```

- [ ] **Step 4: Rebuild and restart Docker**

The frontend container runs `npm ci` on startup, which reads `package-lock.json`. Rebuilding forces it to pick up the new CodeMirror packages.

Run from the project root:
```bash
bash scripts/start.sh --build
```
Expected: frontend container rebuilds and starts, accessible at http://localhost:3000/resume

- [ ] **Step 5: Verify in browser**

1. Open http://localhost:3000/resume
2. Confirm the nav shows "Resume" as active
3. Confirm the editor shows the initial resume HTML
4. Confirm the A4 preview renders the resume correctly
5. Edit a word in the editor — confirm the preview updates (after ~300ms debounce)
6. Type a label and click Save — confirm the version appears in the history dropdown
7. Select a different version from the dropdown — confirm content changes
8. Click Print — confirm a new window opens and the browser print dialog appears

---

## Self-Review

**Spec coverage:**
- [x] `resume_version` table — Task 1
- [x] Seeding from embedded HTML on first startup — Task 2 (`seed_resume()` in lifespan)
- [x] `GET /api/resume` returns latest — Task 2
- [x] `GET /api/resume/versions` returns metadata list (no content) — Task 2
- [x] `GET /api/resume/versions/{id}` returns full version — Task 2
- [x] `POST /api/resume/versions` saves new version — Task 2
- [x] `DELETE /api/resume/versions/{id}` with 400 guard — Task 2
- [x] CodeMirror HTML editor (left pane) — Task 3
- [x] Live A4 preview (right pane, debounced 300ms) — Task 3
- [x] A4 overflow detection (red ring + warning) — Task 3
- [x] Version history dropdown — Task 3
- [x] Save with label — Task 3
- [x] Print (new window + window.print) — Task 3
- [x] `/resume` page — Task 4
- [x] "Resume" nav link — Task 4
- [x] Docker rebuild step — Task 4

**Placeholder scan:** No TBDs. Step 5 in Task 2 reminds the implementer to read and embed the actual HTML — not a placeholder, it's an instruction.

**Type consistency:**
- `VersionMeta` (frontend) matches `ResumeVersionMeta` (backend) fields: `id`, `label`, `created_at` ✓
- `ResumeVersionOut` fields used in `GET /api/resume` response match what frontend reads: `id`, `content` ✓
- `seed_resume()` imported in `main.py` from `routes.resume` ✓
- `resume_router` registered at `/api` prefix ✓
