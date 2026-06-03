# Hidden Jobs Filter

**Date:** 2026-06-03
**Status:** Approved

## Overview

Add a visibility filter that lets users see jobs they have soft-deleted (hidden), and unhide them from that view.

## Backend

### Modified endpoint: `GET /api/jobs`

Add query param:
```
visibility: Literal["visible", "hidden", "all"]  # default: "visible"
```

Current behaviour: always filters `Job.is_hidden == False`.
New behaviour: filter is conditional on `visibility`:
- `"visible"` → `Job.is_hidden == False` (unchanged default)
- `"hidden"` → `Job.is_hidden == True`
- `"all"` → no filter on `is_hidden`

### New endpoint: `PATCH /api/jobs/{job_id}/unhide`

Sets `job.is_hidden = False`. Returns `JobOut`. Mirrors existing `/hide` endpoint.

No model or schema changes required — `is_hidden` is already in `JobOut`.

## Frontend

### `JobList.tsx`

Add `visibility` state (`"visible" | "hidden" | "all"`, default `"visible"`).

Add a select to the filter grid:
- `"visible"` → label "Active jobs"
- `"hidden"` → label "Hidden jobs"
- `"all"` → label "All jobs"

`visibility` is included in:
- URL sync params
- `buildParams` (sent as `visibility` query param)
- `hasActiveFilters` check (`visibility !== "visible"`)
- `resetFilters` (reset to `"visible"`)
- page reset effect deps

Add `onUnhide` handler: calls `PATCH /api/jobs/{id}/unhide`, removes job from local list.

### `JobCard.tsx`

When `job.is_hidden` is true: render "Unhide" button (calls `onUnhide`) instead of "Hide" button.
`onUnhide` prop is optional — existing callers that never show hidden jobs need no change.
