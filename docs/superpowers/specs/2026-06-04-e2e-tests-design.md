# E2E Test Suite Design

Date: 2026-06-04

## Overview

Playwright e2e tests covering the core user flows of the Aus Job Scraper app. Tests run against a real FastAPI backend with a seeded test SQLite database — no mocking.

## Approach

- **Framework**: Playwright, installed as a dev dependency in `frontend/`
- **Locally**: backend starts via Docker Compose (environment guarantee); Next.js runs natively
- **CI (GitHub Actions)**: both backend and Next.js run natively (`uv` for Python, `npm` for Node); Docker not required since GitHub manages the environment
- **Test database**: fresh `data/test.db` seeded before every suite run; dropped and recreated in `global-setup.ts`

## Directory Structure

The `e2e/` directory lives at the repo root, alongside `frontend/` and `backend/`.

```
e2e/
  fixtures/
    seed.py          # inserts test data directly into SQLite test DB
    seed.ts          # called from global-setup, invokes seed.py
  tests/
    job-list.spec.ts
    job-detail.spec.ts
    hide-job.spec.ts
    tags.spec.ts
    notes.spec.ts
    scrape-progress.spec.ts
  playwright.config.ts
  global-setup.ts    # starts backend, seeds DB, starts Next.js dev server
  global-teardown.ts # stops backend and Next.js, cleans up

.github/
  workflows/
    e2e.yml          # triggers on push/PR to main
```

`playwright.config.ts` sets `baseURL: http://localhost:3000` and passes `API_URL=http://localhost:8000` to the Next.js process.

## Test Data

Seeded via `e2e/fixtures/seed.py` (direct SQLite inserts, since there is no `POST /jobs` API endpoint):

- 3 visible jobs — varied titles, companies, locations, salary, tags, notes, listing dates
- 1 hidden job
- 1 reposted job
- 1 job with a company that matches a known sponsor (for SponsorLookup)

The seed script is called from `global-setup.ts` using `execSync('uv run python e2e/fixtures/seed.py')`.

## Test Coverage

### `job-list.spec.ts`
- Jobs appear on the home page
- Sorting by latest/oldest reorders the list
- Keyword filter narrows results
- Hidden jobs do not appear by default

### `job-detail.spec.ts`
- Clicking a job card navigates to its detail page
- Title, company, location, salary, and description render correctly
- "View on Seek" link is present and points to the correct URL
- SponsorLookup badge appears for sponsor companies

### `hide-job.spec.ts`
- "Not interested" hides the job and redirects to home; job absent from list
- Navigating directly to a hidden job shows the "Unhide" button
- Clicking "Unhide" restores the job to the list

### `tags.spec.ts`
- Adding a tag on job detail page causes it to appear
- Refreshing the page shows the tag persisted
- Removing a tag causes it to disappear

### `notes.spec.ts`
- Typing a note and saving it; refreshing confirms the note persisted

### `scrape-progress.spec.ts`
- Triggering a scrape shows the progress indicator
- The cancel button appears while running; clicking it resets the status

## CI Workflow (GitHub Actions)

```yaml
# .github/workflows/e2e.yml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.13' }
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - run: pip install uv
      - run: cd backend && uv sync
      - run: cd frontend && npm ci
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000
          DATABASE_URL: sqlite:///./data/test.db
```

## Success Criteria

- All 6 test files pass locally and in CI
- Tests are isolated — each run starts from a clean seeded DB
- CI runs complete in under 5 minutes on a cold GitHub Actions runner
- No tests depend on live Seek.com.au network access
