# Resume Editor — Design Spec

## Goal

A resume editing page within the job scraper app. The user can edit their resume as raw HTML in a split-pane editor with a live A4 preview, save named versions to the database, restore any previous version, and print to A4 PDF via the browser.

---

## Data Model

### Table: `resume_version`

| column | type | constraints | notes |
|---|---|---|---|
| `id` | INTEGER | PK autoincrement | |
| `label` | TEXT | NOT NULL | user-provided name e.g. "Backend roles v2" |
| `content` | TEXT | NOT NULL | full HTML document string |
| `created_at` | DATETIME | NOT NULL, default now | |

**Seeding:** On first startup, if the table is empty, the backend reads `backend/data/resume-init.html` and inserts it as version 1 with label `"Initial"`.

**Current version:** The row with the highest `id` (most recently inserted). No separate pointer column needed.

---

## Backend

### New files
- `backend/alembic/versions/0007_add_resume_version.py` — migration
- `backend/routes/resume.py` — API router
- `backend/tests/test_resume.py` — tests

### Modified files
- `backend/models.py` — add `ResumeVersion` SQLModel
- `backend/main.py` — register resume router at `/api`

### SQLModel

```python
class ResumeVersion(SQLModel, table=True):
    __tablename__ = "resume_version"
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### API Endpoints

| method | path | description |
|---|---|---|
| GET | `/api/resume` | Returns latest version (highest id). 404 if none exist. |
| GET | `/api/resume/versions` | Returns list of all versions ordered by id desc — `id`, `label`, `created_at` only (no `content`). |
| GET | `/api/resume/versions/{id}` | Returns full version including `content`. 404 if not found. |
| POST | `/api/resume/versions` | Body: `{label: str, content: str}`. Saves new version. Returns created version. |
| DELETE | `/api/resume/versions/{id}` | Deletes version. Returns 400 if it would delete the last remaining version. |

### Seeding

In `backend/routes/resume.py`, a `seed_resume` function reads `data/resume-init.html` relative to the backend working directory and inserts it if the table is empty. Called from `lifespan` in `main.py` after `create_db()`.

---

## Frontend

### New files
- `frontend/app/resume/page.tsx` — Resume page
- `frontend/components/ResumeEditor.tsx` — split-pane editor component

### Modified files
- `frontend/components/Nav.tsx` — add "Resume" link
- `frontend/app/layout.tsx` — no change needed (Nav update is sufficient)

### Dependencies
- `@uiw/react-codemirror` — CodeMirror 6 React wrapper
- `@codemirror/lang-html` — HTML language support for syntax highlighting

### Page layout

`/resume` renders `<ResumeEditor />` which is a client component with:

**Left pane (45% width):** CodeMirror editor initialized with current resume HTML. Updates `content` state on every keystroke.

**Right pane (55% width):** An `<iframe>` with `srcDoc={content}` and fixed dimensions `width: 210mm; height: 297mm`. The iframe re-renders on content change (debounced 300ms to avoid excessive re-renders). An overflow check runs after each render: if `iframe.contentDocument.body.scrollHeight > 297mm in px (1122px)`, show a red "Overflows A4" warning below the preview.

**Bottom toolbar:**
- **Version history dropdown** — populated from `GET /api/resume/versions`. Selecting an entry calls `GET /api/resume/versions/{id}` and loads the content into the editor. Does not auto-save.
- **Label input** — free-text field for the save label.
- **Save button** — calls `POST /api/resume/versions` with current `content` and label. On success, refreshes the versions list and selects the new version.
- **Print button** — calls `window.print()`. The resume HTML includes `@page { size: A4; margin: 0; }` so the browser print dialog locks to one A4 page.

### A4 overflow detection

```
A4 height at 96dpi = 297mm × (96/25.4) ≈ 1122px
```

After each content change (debounced 300ms), check `iframe.contentDocument?.documentElement?.scrollHeight`. If it exceeds 1122px, show warning. Use a `useEffect` watching the debounced content value — `srcDoc` changes do not reliably re-fire the iframe `load` event.

### Print behaviour

The Print button calls `window.print()` from the main page. This would print the entire app page, not just the resume. Instead, the button opens the resume HTML in a new window and calls `print()` on that window:

```ts
const win = window.open("", "_blank");
win.document.write(content);
win.document.close();
win.print();
```

The resume's existing CSS already handles fonts and layout. The only addition needed is appending `@page { size: A4 portrait; margin: 0; }` to the `<head>` before writing if not already present — but since the user controls the HTML directly, this is their responsibility. A helper note in the UI ("Make sure your HTML includes @page CSS for accurate printing") covers this.

---

## Testing

`backend/tests/test_resume.py` covers:
- `GET /api/resume` returns 404 on empty table
- Seeding inserts initial version from file
- `POST /api/resume/versions` creates and returns a version
- `GET /api/resume` returns the latest version
- `GET /api/resume/versions` returns list without content
- `GET /api/resume/versions/{id}` returns full content
- `DELETE /api/resume/versions/{id}` deletes a version
- `DELETE` returns 400 when only one version remains

---

## Out of Scope

- Exporting to Word/PDF server-side
- Diff view between versions
- Sharing or public resume URL
- Multiple resumes
