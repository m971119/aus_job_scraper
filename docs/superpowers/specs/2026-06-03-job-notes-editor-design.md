# Job Notes Editor

**Date:** 2026-06-03
**Status:** Approved

## Overview

Add a `notes` field to jobs. On the detail page, a TipTap rich-text editor lets the user write formatted notes per job. Notes are stored as HTML in SQLite and rendered as HTML in the frontend.

## Decisions

- **Editor library:** TipTap (React-first, modular, outputs HTML directly)
- **Interaction mode:** View/edit toggle — rendered HTML by default, click "Edit" to open editor, auto-saves on blur
- **Toolbar:** Bold, Italic, Underline, BulletList, OrderedList, Link
- **Placement:** Job detail page only (not on job cards)

## Backend

### Model (`backend/models.py`)

Add to `Job`:

```python
notes: Optional[str] = None  # stores HTML
```

### Migration (`backend/alembic/versions/0005_add_notes.py`)

```python
revision = "0005"
down_revision = "0004"

def upgrade():
    op.add_column("job", sa.Column("notes", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("job", "notes")
```

### Schema (`backend/schemas.py`)

Add to `JobOut`:

```python
notes: Optional[str] = None
```

### Endpoint (`backend/routes/jobs.py`)

```
PATCH /api/jobs/{job_id}/notes
Body: { "notes": str | null }
Response: JobOut
Returns 404 if job not found
```

Update `_to_out` to include `notes=j.notes`.

## Frontend

### Types (`frontend/types/index.ts` or equivalent)

Add to `Job`:

```ts
notes?: string | null;
```

### `NotesEditor` component (`frontend/components/NotesEditor.tsx`)

**Props:**
```ts
interface Props {
  jobId: number;
  initialNotes: string | null;
}
```

**Behaviour:**

- State: `editing: boolean` (default `false`), `html: string | null` (current rendered content, initialised from `initialNotes`)
- **View mode:** `div` renders `html` via `dangerouslySetInnerHTML`. If `html` is empty/null, shows `"No notes yet."` in muted text. "Edit" button top-right switches to edit mode.
- **Edit mode:** TipTap editor initialised with `html`. Blue focus ring (`ring-2 ring-primary/30 border-primary`). Hint text "Saves on close" replaces the Edit button. On TipTap `onBlur`: call `PATCH /api/jobs/{jobId}/notes` with `{ notes: editor.getHTML() }`, update `html` state, set `editing` to `false`.
- Empty editor (no content): save `null` rather than `<p></p>`.

**npm packages to install** (in `frontend/`):
```
@tiptap/react @tiptap/pm @tiptap/starter-kit @tiptap/extension-underline @tiptap/extension-link
```

**TipTap extensions used:**
- `StarterKit` (includes Bold, Italic, BulletList, OrderedList, Paragraph, History)
- `Underline`
- `Link` (with `openOnClick: false`)

**Toolbar buttons** (shown only in edit mode, above editor):
Bold · Italic · Underline · [divider] · BulletList · OrderedList · Link

### Detail page (`frontend/app/jobs/[id]/page.tsx`)

Add `<NotesEditor jobId={job.id} initialNotes={job.notes ?? null} />` below `<TagManager />`.

## Data flow

```
User clicks Edit
  → TipTap editor opens with current HTML
  → User types / formats
  → User clicks away (blur)
  → PATCH /api/jobs/{id}/notes  { notes: "<p>...</p>" }
  → Response: updated JobOut
  → View mode renders new HTML
```

## Testing

- Backend: unit tests for `PATCH /notes` — success, 404, null body clears notes
- No frontend unit tests required (TipTap is a third-party library)
