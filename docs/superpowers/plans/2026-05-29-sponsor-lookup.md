# Sponsor Lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-job "Sponsor?" popover to each job card that lets the user fuzzy-search `backend/data/sponsors.txt` by company name and decide whether to manually tag the job.

**Architecture:** The backend loads `sponsors.txt` once at startup and exposes it via `GET /api/sponsors`. The frontend fetches that list once (in `JobList`), passes it to each `JobCard`, which renders a `SponsorLookup` popover pre-filled with the job's company name and using Fuse.js for client-side fuzzy matching.

**Tech Stack:** FastAPI (backend endpoint), Fuse.js v7 (client-side fuzzy search), React (popover component), Next.js App Router.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/routes/sponsors.py` | Create | Load sponsors.txt; serve list via GET /api/sponsors |
| `backend/main.py` | Modify | Register sponsors router |
| `backend/tests/test_sponsors.py` | Create | Tests for the sponsors endpoint |
| `frontend/components/SponsorLookup.tsx` | Create | Popover with fuzzy-search input and results |
| `frontend/components/JobCard.tsx` | Modify | Add sponsors prop + "Sponsor?" button next to company |
| `frontend/components/JobList.tsx` | Modify | Fetch sponsors list; pass to JobCard |

---

### Task 1: Backend — sponsors endpoint

**Files:**
- Create: `backend/routes/sponsors.py`
- Create: `backend/tests/test_sponsors.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sponsors.py`:

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_sponsors_returns_200():
    resp = client.get("/api/sponsors")
    assert resp.status_code == 200


def test_sponsors_returns_list_of_strings():
    resp = client.get("/api/sponsors")
    data = resp.json()
    assert "sponsors" in data
    assert isinstance(data["sponsors"], list)
    assert all(isinstance(s, str) for s in data["sponsors"])


def test_sponsors_list_is_nonempty():
    resp = client.get("/api/sponsors")
    assert len(resp.json()["sponsors"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
uv run pytest tests/test_sponsors.py -v
```

Expected: FAIL — `404 Not Found` (route doesn't exist yet).

- [ ] **Step 3: Create the sponsors route**

Create `backend/routes/sponsors.py`:

```python
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

_DATA_FILE = Path(__file__).parent.parent / "data" / "sponsors.txt"
_sponsors: list[str] = [
    line.strip()
    for line in _DATA_FILE.read_text(encoding="utf-8").splitlines()
    if line.strip()
]


@router.get("/sponsors")
def list_sponsors():
    return {"sponsors": _sponsors}
```

- [ ] **Step 4: Register the router in main.py**

In `backend/main.py`, add after the existing route imports:

```python
from routes import jobs, scrape, tags, sponsors
```

And after the existing `app.include_router` calls:

```python
app.include_router(sponsors.router, prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
uv run pytest tests/test_sponsors.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/sponsors.py backend/tests/test_sponsors.py backend/main.py
git commit -m "feat(sponsors): add GET /api/sponsors endpoint"
```

---

### Task 2: Frontend — install Fuse.js and fetch sponsors in JobList

**Files:**
- Modify: `frontend/components/JobList.tsx`
- Modify: `frontend/components/JobCard.tsx` (props only, no UI yet)

- [ ] **Step 1: Install Fuse.js**

```bash
cd frontend
npm install fuse.js
```

Expected: `fuse.js` appears in `package.json` dependencies.

- [ ] **Step 2: Add sponsors fetch to JobList**

In `frontend/components/JobList.tsx`, add a `sponsors` state after the `allTags` state:

```typescript
const [allTags, setAllTags] = useState<Tag[]>([]);
const [sponsors, setSponsors] = useState<string[]>([]);
```

Add a fetch effect after the existing tags fetch effect:

```typescript
useEffect(() => {
  fetch(`${API}/api/sponsors`).then((r) => r.json()).then((d) => setSponsors(d.sponsors));
}, []);
```

Pass `sponsors` to each `JobCard` in the render:

```tsx
<JobCard key={job.id} job={job} allTags={allTags} sponsors={sponsors} onHide={handleHide} />
```

- [ ] **Step 3: Add sponsors prop to JobCard**

In `frontend/components/JobCard.tsx`, update the `Props` interface:

```typescript
interface Props {
  job: Job;
  allTags: Tag[];
  sponsors: string[];
  onHide?: (id: number) => void;
}
```

Update the function signature:

```typescript
export default function JobCard({ job, allTags, sponsors, onHide }: Props) {
```

- [ ] **Step 4: Type-check**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/JobList.tsx frontend/components/JobCard.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat(sponsors): fetch sponsor list in JobList; thread to JobCard"
```

---

### Task 3: Frontend — SponsorLookup component

**Files:**
- Create: `frontend/components/SponsorLookup.tsx`

- [ ] **Step 1: Create SponsorLookup.tsx**

Create `frontend/components/SponsorLookup.tsx`:

```typescript
"use client";
import { useState, useEffect, useRef, useMemo } from "react";
import Fuse from "fuse.js";

interface Props {
  companyName: string;
  sponsors: string[];
}

export default function SponsorLookup({ companyName, sponsors }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleOpen = () => {
    setQuery(companyName);
    setOpen(true);
  };

  const fuse = useMemo(
    () => new Fuse(sponsors, { threshold: 0.4, includeScore: true }),
    [sponsors]
  );

  const results = useMemo(
    () => (query ? fuse.search(query).slice(0, 8) : []),
    [fuse, query]
  );

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={handleOpen}
        className="text-xs text-muted hover:text-primary border border-gray-200 hover:border-primary px-2 py-0.5 rounded transition-colors"
      >
        Sponsor?
      </button>

      {open && (
        <div className="absolute z-20 left-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="Search sponsor list..."
            autoFocus
          />
          <div className="mt-2 max-h-48 overflow-y-auto space-y-0.5">
            {query && results.length === 0 && (
              <p className="text-xs text-muted py-2 text-center">No matches found</p>
            )}
            {results.map(({ item, score }) => (
              <div
                key={item}
                className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-gray-50 text-sm"
              >
                <span className="text-gray-700 truncate mr-2">{item}</span>
                <span
                  className={`shrink-0 text-xs font-medium px-1.5 py-0.5 rounded ${
                    (score ?? 1) < 0.2
                      ? "bg-green-100 text-green-700"
                      : (score ?? 1) < 0.4
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {(score ?? 1) < 0.2 ? "Strong" : (score ?? 1) < 0.4 ? "Likely" : "Weak"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/SponsorLookup.tsx
git commit -m "feat(sponsors): add SponsorLookup fuzzy-search popover"
```

---

### Task 4: Frontend — wire SponsorLookup into JobCard

**Files:**
- Modify: `frontend/components/JobCard.tsx`

- [ ] **Step 1: Add SponsorLookup to the company name line**

In `frontend/components/JobCard.tsx`, add the import at the top:

```typescript
import SponsorLookup from "./SponsorLookup";
```

Replace the existing company paragraph:

```tsx
{job.company && (
  <p className="text-navy font-medium mt-0.5">{job.company}</p>
)}
```

With:

```tsx
{job.company && (
  <div className="flex items-center gap-2 mt-0.5">
    <p className="text-navy font-medium">{job.company}</p>
    <SponsorLookup companyName={job.company} sponsors={sponsors} />
  </div>
)}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run backend tests to confirm nothing broke**

```bash
cd backend
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/JobCard.tsx
git commit -m "feat(sponsors): wire SponsorLookup into JobCard"
```
