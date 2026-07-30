# AI Batch Job Filter — Design Spec

**Date:** 2026-07-30
**Implementation branch:** new branch off `main`, e.g. `feat/ai-batch-filter`

## Overview

A manually-triggered batch service that uses an LLM to filter out irrelevant jobs from the scraped list. The user triggers it from a dedicated `/ai-filter` page. The AI hides jobs that clearly don't match the candidate's profile (rules-only, no resume sent). A `hide_reason` field records why each job was hidden — either by the AI or by the user.

---

## Data Model

### New column: `Job.hide_reason: Optional[str]`

| Value | Meaning |
|---|---|
| `null` | Not hidden, or hidden without a recorded reason (legacy rows) |
| `"USER"` | User clicked "Not interested" |
| Any other string | AI-generated reason (e.g. `"Requires ASP.NET"`) |

**Migration:** `0009_add_hide_reason.py` — adds nullable `hide_reason TEXT` column to the `job` table.

**Schema change:** `JobOut` gains `hide_reason: Optional[str]`.

**Hide endpoint change:** `PATCH /api/jobs/{job_id}/hide` always writes `hide_reason = "USER"` alongside `is_hidden = True`. No request body change needed.

---

## Backend

### New file: `backend/ai_filter_service.py`

Core batch filtering logic:

1. Query all `Job` rows where `is_hidden = False`
2. Strip HTML from descriptions (`strip_html` from `ai_config.py`)
3. Chunk into batches of 20 jobs
4. Per batch: one `litellm` call (default model: `gpt-4o-mini`) with a system prompt containing exclusion rules, asking for structured JSON output
5. Parse response: `[{id: int, hide: bool, reason: str}]`
6. For each `hide=true` entry: set `is_hidden=True`, `hide_reason=<reason>`, commit to DB
7. Update shared in-memory status dict after each batch

**LLM input per job:** title + first 500 chars of plain-text description.

**Exclusion rules in system prompt:**
- Leadership-only roles: Principal Engineer, Engineering Lead/Manager, VP/Director of Engineering
- Non-software PM roles: Project Manager or Product Manager for construction, infrastructure, or non-tech domains
- Non-software engineering disciplines: Electrical Engineer, Civil Engineer, Mechanical Engineer, Structural Engineer
- Roles requiring ASP.NET as a core/mandatory skill
- Any other role clearly outside software/web/data engineering

**Structured output format requested from LLM:**
```json
[
  {"id": 123, "hide": true, "reason": "Civil engineering role"},
  {"id": 124, "hide": false, "reason": ""}
]
```

The system prompt must instruct the model to keep `reason` under 60 characters — a short label, not a sentence.

### Shared status dict (in-memory, same pattern as scraper):

```python
{
  "status": "idle" | "running" | "done" | "cancelled" | "error",
  "current_batch": int,
  "total_batches": int,
  "evaluated": int,
  "hidden": int,
  "error": str | None
}
```

### New file: `backend/routes/ai_filter.py`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/ai-filter/run` | Start background filter task; 409 if already running |
| `GET` | `/api/ai-filter/status` | Return current status dict |
| `POST` | `/api/ai-filter/cancel` | Signal cancellation |

Registered in `main.py` under the `/api` prefix.

---

## Frontend

### New page: `frontend/app/ai-filter/page.tsx`

Layout:
- **Header:** "AI Job Filter" + one-line description
- **Run button:** "Run Filter" — disabled and shows "Running..." while status is `running`
- **Progress:** visible while running — `"Batch {current_batch} / {total_batches} — {evaluated} evaluated, {hidden} hidden"`; polls `/api/ai-filter/status` every 1.5 s
- **Result summary:** shown when status is `done` — `"Done — {hidden} jobs hidden out of {evaluated} evaluated"`
- **Error state:** shown when status is `error`

Polls status on mount to restore UI if a run is already in progress.

### Nav link

Add "AI Filter" link to `frontend/components/Nav.tsx`.

### Hide reason display

In `frontend/components/JobCard.tsx`, when `job.is_hidden` is true and `job.hide_reason` is set, show a small label beneath the title:

- `hide_reason === "USER"` → `"Hidden by: You"`
- otherwise → `"Hidden by: AI — {hide_reason}"`

This is visible when the user filters the job list to `visibility=hidden`.

---

## Error handling

- If an LLM batch call fails, log the error, mark status as `error`, stop processing. Already-processed batches retain their results.
- If JSON parsing of LLM response fails for a batch, skip that batch (don't hide anything from it) and continue.

---

## Out of scope

- Resume-aware filtering (rules-only, no resume sent)
- Auto-run after scrape
- Re-run / reset mechanics (re-evaluates all visible jobs on every manual run)
- Per-job AI filter history
