# Job Notes Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-job `notes` field (stored as HTML) with a TipTap rich-text editor on the job detail page.

**Architecture:** Backend adds the `notes` column via Alembic migration, exposes it in `JobOut`, and adds a `PATCH /notes` endpoint. Frontend installs TipTap, adds a `NotesEditor` component with view/edit toggle, and wires it into the detail page.

**Tech Stack:** FastAPI, SQLModel, Alembic, Next.js 16, TipTap (`@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/extension-underline`, `@tiptap/extension-link`), Tailwind CSS v4

---

## File Map

| File | Action |
|------|--------|
| `backend/models.py` | Add `notes` field to `Job` |
| `backend/alembic/versions/0005_add_notes.py` | Create migration |
| `backend/schemas.py` | Add `notes` to `JobOut`, add `NotesUpdate` |
| `backend/routes/jobs.py` | Add `PATCH /jobs/{id}/notes`, update `_to_out` |
| `backend/tests/test_api.py` | Add 4 tests for notes endpoint |
| `frontend/types.ts` | Add `notes` to `Job` interface |
| `frontend/app/globals.css` | Add `.notes-content` prose styles |
| `frontend/components/NotesEditor.tsx` | New TipTap editor component |
| `frontend/app/jobs/[id]/page.tsx` | Mount `NotesEditor` below `TagManager` |

---

### Task 1: Backend — model, migration, schema, endpoint

**Files:**
- Modify: `backend/models.py`
- Create: `backend/alembic/versions/0005_add_notes.py`
- Modify: `backend/schemas.py`
- Modify: `backend/routes/jobs.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to the end of `backend/tests/test_api.py`:

```python
def test_update_notes():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    resp = client.patch(f"/api/jobs/{job_id}/notes", json={"notes": "<p>Great role</p>"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "<p>Great role</p>"


def test_update_notes_clears_to_null():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    client.patch(f"/api/jobs/{job_id}/notes", json={"notes": "<p>Old notes</p>"})
    resp = client.patch(f"/api/jobs/{job_id}/notes", json={"notes": None})
    assert resp.status_code == 200
    assert resp.json()["notes"] is None


def test_update_notes_not_found():
    resp = client.patch("/api/jobs/99999/notes", json={"notes": "<p>Test</p>"})
    assert resp.status_code == 404


def test_notes_returned_in_job_list():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    client.patch(f"/api/jobs/{job_id}/notes", json={"notes": "<p>Some notes</p>"})
    resp = client.get("/api/jobs")
    assert resp.json()["items"][0]["notes"] == "<p>Some notes</p>"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/michilin19/Personal/Projects/aus_job_scraper/backend
uv run pytest tests/test_api.py::test_update_notes tests/test_api.py::test_update_notes_clears_to_null tests/test_api.py::test_update_notes_not_found tests/test_api.py::test_notes_returned_in_job_list -v
```

Expected: all 4 FAIL (endpoint not found / `notes` not in response).

- [ ] **Step 3: Add `notes` field to the `Job` model**

In `backend/models.py`, add one line to the `Job` class after `is_hidden`:

```python
    notes: Optional[str] = None
```

The full `Job` class should now end with:

```python
    is_repost: bool = Field(default=False)
    is_hidden: bool = Field(default=False)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Create the Alembic migration**

Create `backend/alembic/versions/0005_add_notes.py`:

```python
"""add notes column to job

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-03
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {col["name"] for col in inspect(conn).get_columns("job")}
    if "notes" not in columns:
        op.add_column("job", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("job", "notes")
```

- [ ] **Step 5: Run the migration**

```bash
cd /Users/michilin19/Personal/Projects/aus_job_scraper/backend
uv run alembic upgrade head
```

Expected: output ending with `Running upgrade 0004 -> 0005, add notes column to job`

- [ ] **Step 6: Add `NotesUpdate` schema and `notes` to `JobOut`**

In `backend/schemas.py`, add `NotesUpdate` after `TagCreate`:

```python
class NotesUpdate(BaseModel):
    notes: Optional[str] = None
```

Add `notes` to `JobOut`:

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
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 7: Add the `PATCH /notes` endpoint and update `_to_out`**

In `backend/routes/jobs.py`, add to the imports line:

```python
from schemas import JobOut, JobsPage, NotesUpdate, TagOut
```

Add the new endpoint after `unhide_job`:

```python
@router.patch("/jobs/{job_id}/notes", response_model=JobOut)
def update_notes(job_id: int, body: NotesUpdate, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.notes = body.notes
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)
```

Update `_to_out` to include `notes`:

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
        notes=j.notes,
        tags=_get_job_tags(session, j.id),
    )
```

- [ ] **Step 8: Run all 4 new tests**

```bash
cd /Users/michilin19/Personal/Projects/aus_job_scraper/backend
uv run pytest tests/test_api.py::test_update_notes tests/test_api.py::test_update_notes_clears_to_null tests/test_api.py::test_update_notes_not_found tests/test_api.py::test_notes_returned_in_job_list -v
```

Expected: all 4 PASS.

- [ ] **Step 9: Run full backend test suite**

```bash
cd /Users/michilin19/Personal/Projects/aus_job_scraper/backend
uv run pytest tests/test_api.py -v
```

Expected: all tests in `test_api.py` pass (pre-existing `test_get_jobs_returns_listed_dates_as_list` failure is unrelated and can be ignored).

- [ ] **Step 10: Commit**

```bash
git -C /Users/michilin19/Personal/Projects/aus_job_scraper add \
  backend/models.py \
  backend/alembic/versions/0005_add_notes.py \
  backend/schemas.py \
  backend/routes/jobs.py \
  backend/tests/test_api.py
git -C /Users/michilin19/Personal/Projects/aus_job_scraper commit -m "feat(jobs): add notes field with PATCH endpoint"
```

---

### Task 2: Frontend — types, CSS, and NotesEditor component

**Files:**
- Modify: `frontend/types.ts`
- Modify: `frontend/app/globals.css`
- Create: `frontend/components/NotesEditor.tsx`

- [ ] **Step 1: Install TipTap packages**

```bash
cd /Users/michilin19/Personal/Projects/aus_job_scraper/frontend
npm install @tiptap/react @tiptap/pm @tiptap/starter-kit @tiptap/extension-underline @tiptap/extension-link
```

Expected: packages added to `package.json` and `node_modules`.

- [ ] **Step 2: Add `notes` to the `Job` type**

In `frontend/types.ts`, add `notes` to the `Job` interface:

```typescript
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
  notes: string | null;
  tags: Tag[];
}
```

- [ ] **Step 3: Add `.notes-content` prose styles to globals.css**

Append to `frontend/app/globals.css`:

```css
.notes-content p { margin: 0.25rem 0; }
.notes-content ul { list-style: disc; padding-left: 1.25rem; margin: 0.25rem 0; }
.notes-content ol { list-style: decimal; padding-left: 1.25rem; margin: 0.25rem 0; }
.notes-content li { margin: 0.1rem 0; }
.notes-content a { color: #209dd7; text-decoration: underline; }
.notes-content strong { font-weight: 600; }
.notes-content em { font-style: italic; }
.notes-content u { text-decoration: underline; }
```

- [ ] **Step 4: Create `NotesEditor.tsx`**

Create `frontend/components/NotesEditor.tsx`:

```tsx
"use client";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Link from "@tiptap/extension-link";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  jobId: number;
  initialNotes: string | null;
}

function ToolbarBtn({
  onClick,
  active,
  children,
}: {
  onClick: () => void;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => {
        e.preventDefault();
        onClick();
      }}
      className={`px-2 py-0.5 text-xs border rounded transition-colors ${
        active
          ? "border-primary bg-primary/10 text-primary"
          : "border-gray-200 bg-white text-gray-600 hover:border-primary hover:text-primary"
      }`}
    >
      {children}
    </button>
  );
}

export default function NotesEditor({ jobId, initialNotes }: Props) {
  const [editing, setEditing] = useState(false);
  const [html, setHtml] = useState<string | null>(initialNotes);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Link.configure({ openOnClick: false }),
    ],
    content: html ?? "",
    editorProps: {
      attributes: {
        class:
          "notes-content outline-none min-h-[80px] px-3 py-2.5 text-sm leading-relaxed",
      },
    },
    onBlur: async ({ editor }) => {
      const content = editor.isEmpty ? null : editor.getHTML();
      setHtml(content);
      setEditing(false);
      await fetch(`${API}/api/jobs/${jobId}/notes`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: content }),
      });
    },
  });

  const handleEdit = () => {
    editor?.commands.setContent(html ?? "");
    setEditing(true);
    setTimeout(() => editor?.commands.focus(), 0);
  };

  const setLink = () => {
    if (!editor) return;
    const url = window.prompt("URL");
    if (url) editor.chain().focus().setLink({ href: url }).run();
    else editor.chain().focus().unsetLink().run();
  };

  return (
    <div className="mt-6 pt-5 border-t border-gray-100">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-navy">Notes</h2>
        {editing ? (
          <span className="text-xs text-muted italic">Saves on close</span>
        ) : (
          <button
            onClick={handleEdit}
            className="text-xs text-muted hover:text-primary border border-gray-200 hover:border-primary px-2 py-0.5 rounded transition-colors"
          >
            ✏ Edit
          </button>
        )}
      </div>

      {editing ? (
        <div className="border border-primary rounded-lg overflow-hidden ring-2 ring-primary/20">
          <div className="flex flex-wrap gap-1 px-2 py-1.5 bg-gray-50 border-b border-gray-200">
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleBold().run()}
              active={editor?.isActive("bold")}
            >
              <strong>B</strong>
            </ToolbarBtn>
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleItalic().run()}
              active={editor?.isActive("italic")}
            >
              <em>I</em>
            </ToolbarBtn>
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleUnderline().run()}
              active={editor?.isActive("underline")}
            >
              <span className="underline">U</span>
            </ToolbarBtn>
            <div className="w-px bg-gray-200 mx-0.5" />
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleBulletList().run()}
              active={editor?.isActive("bulletList")}
            >
              • List
            </ToolbarBtn>
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleOrderedList().run()}
              active={editor?.isActive("orderedList")}
            >
              1. List
            </ToolbarBtn>
            <ToolbarBtn onClick={setLink} active={editor?.isActive("link")}>
              Link
            </ToolbarBtn>
          </div>
          <EditorContent editor={editor} />
        </div>
      ) : (
        <div
          onClick={handleEdit}
          className="cursor-pointer px-3 py-2.5 border border-gray-200 rounded-lg bg-gray-50 min-h-[60px] hover:border-primary/40 transition-colors"
        >
          {html ? (
            <div
              className="notes-content text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          ) : (
            <p className="text-muted text-sm italic">No notes yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/michilin19/Personal/Projects/aus_job_scraper add \
  frontend/types.ts \
  frontend/app/globals.css \
  frontend/components/NotesEditor.tsx \
  frontend/package.json \
  frontend/package-lock.json
git -C /Users/michilin19/Personal/Projects/aus_job_scraper commit -m "feat(frontend): add NotesEditor component with TipTap"
```

---

### Task 3: Frontend — wire NotesEditor into the detail page

**Files:**
- Modify: `frontend/app/jobs/[id]/page.tsx`

- [ ] **Step 1: Import `NotesEditor`**

Add to the imports in `frontend/app/jobs/[id]/page.tsx`:

```tsx
import NotesEditor from "@/components/NotesEditor";
```

- [ ] **Step 2: Mount `NotesEditor` below `TagManager`**

In `frontend/app/jobs/[id]/page.tsx`, find the `<TagManager ... />` line and add `NotesEditor` directly after it:

```tsx
        <TagManager jobId={job.id} initialTags={job.tags ?? []} />

        <NotesEditor jobId={job.id} initialNotes={job.notes ?? null} />
```

The section of the file around this change should look like:

```tsx
        <TagManager jobId={job.id} initialTags={job.tags ?? []} />

        <NotesEditor jobId={job.id} initialNotes={job.notes ?? null} />

        <div className="mt-6 flex items-center gap-3">
```

- [ ] **Step 3: Verify TypeScript compiles cleanly**

```bash
cd /Users/michilin19/Personal/Projects/aus_job_scraper/frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git -C /Users/michilin19/Personal/Projects/aus_job_scraper add "frontend/app/jobs/[id]/page.tsx"
git -C /Users/michilin19/Personal/Projects/aus_job_scraper commit -m "feat(frontend): wire NotesEditor into job detail page"
```
