# Filter Upgrade Design

**Date:** 2026-05-27
**Status:** Approved

## Summary

Extend the job list filter with two new capabilities:
1. A repost status filter (All / Originals only / Reposts only)
2. Combined tag filtering: include tag (must have) and exclude tag (must not have), both active simultaneously

## Approach

Extend the existing `GET /api/jobs` endpoint with new query params. No new endpoints, no schema changes.

## Backend

### API changes — `GET /api/jobs`

| Param | Type | Default | Behaviour |
|---|---|---|---|
| `include_tag` | string (optional) | — | Replaces existing `tag` param. Jobs must have a tag matching this name (case-insensitive). |
| `exclude_tag` | string (optional) | — | New. Jobs must NOT have a tag matching this name (case-insensitive). Implemented as `NOT EXISTS` subquery on `JobTag`/`Tag`. |
| `is_repost` | `all` \| `originals` \| `reposts` | `all` | New. Adds `WHERE Job.is_repost = true/false` when not `all`. |

Filters are applied in order and are all additive (`AND`):
1. `is_hidden = False`
2. `include_tag` JOIN if present
3. `exclude_tag` NOT EXISTS subquery if present
4. `is_repost` WHERE clause if not `all`
5. Sort → paginate

### File changes

- `backend/routes/jobs.py` — rename `tag` param to `include_tag`, add `exclude_tag` and `is_repost` params, implement SQL logic

### Tests

- `backend/tests/test_tag_filter.py` — rename all `tag=` usages to `include_tag=`; add tests for `exclude_tag` alone, `include_tag` + `exclude_tag` combined, `include_tag` + `is_repost` combined
- `backend/tests/test_repost_filter.py` — new file; tests for `originals`, `reposts`, `all` (default)

## Frontend

### UI changes — `JobList.tsx`

- Rename `tag` state to `includeTag`; send as `include_tag` query param
- Add `excludeTag` state (default `""`); send as `exclude_tag` query param
- Add `isRepost` state typed `"all" | "originals" | "reposts"` (default `"all"`); send as `is_repost` query param
- Filter bar additions (fits into existing flex row pattern):
  - Second `<select>` — label context "Excl. tag", options: "Any tag" + all tags
  - Third `<select>` — options: "All jobs" / "Originals only" / "Reposts only"

No changes to `JobCard`, `page.tsx`, backend models, or DB schema.

## Data flow example

User selects: Include = Python, Exclude = Not interested, Originals only

```
GET /api/jobs?include_tag=Python&exclude_tag=Not+interested&is_repost=originals&sort=latest&page=1&page_size=25
```

Response: same `JobsPage` shape as today.

## Out of scope

- Multi-tag include/exclude (selecting more than one tag per include/exclude)
- Persisting filter state across page reloads
