# Listing Tag Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to add and remove tags directly from the job listing card without navigating to the detail page.

**Architecture:** `JobCard` becomes a client component holding local `tags` and `panelOpen` state. `JobList` already fetches `allTags` for its filter dropdown — it passes that list down as a prop to each `JobCard`, avoiding any new API calls. A `+` circle button in the tag row toggles an inline panel showing all tags as one-click chips (blue = applied, gray = unapplied).

**Tech Stack:** Next.js 15, React, TypeScript, Tailwind CSS (with project theme tokens: `text-primary`, `text-muted`, `text-navy`, `text-accent`, `text-secondary`). API already exists at `POST/DELETE /api/jobs/{id}/tags/{tagId}`.

---

### Task 1: Update `JobList` to pass `allTags` to `JobCard`

**Files:**
- Modify: `frontend/components/JobList.tsx`
- Modify: `frontend/components/JobCard.tsx` (prop type only — no behaviour change yet)

- [ ] **Step 1: Add `allTags` prop to `JobCard`'s Props interface**

Open `frontend/components/JobCard.tsx`. Change the Props interface from:

```tsx
interface Props {
  job: Job;
  onHide?: (id: number) => void;
}
```

to:

```tsx
interface Props {
  job: Job;
  allTags: Tag[];
  onHide?: (id: number) => void;
}
```

Also add the import at the top of the file (it already imports `Job` from `@/types`):

```tsx
import { Job, Tag } from "@/types";
```

And update the component signature:

```tsx
export default function JobCard({ job, allTags, onHide }: Props) {
```

- [ ] **Step 2: Pass `allTags` from `JobList` to each `JobCard`**

Open `frontend/components/JobList.tsx`. Find the line:

```tsx
<JobCard key={job.id} job={job} onHide={handleHide} />
```

Change it to:

```tsx
<JobCard key={job.id} job={job} allTags={allTags} onHide={handleHide} />
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/JobCard.tsx frontend/components/JobList.tsx
git commit -m "feat(tags): add allTags prop to JobCard"
```

---

### Task 2: Convert `JobCard` to a client component with local tag state

**Files:**
- Modify: `frontend/components/JobCard.tsx`

- [ ] **Step 1: Add `"use client"` and local state**

Replace the top of `frontend/components/JobCard.tsx` with:

```tsx
"use client";
import { useState } from "react";
import Link from "next/link";
import { Job, Tag } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  job: Job;
  allTags: Tag[];
  onHide?: (id: number) => void;
}

export default function JobCard({ job, allTags, onHide }: Props) {
  const [tags, setTags] = useState<Tag[]>(job.tags ?? []);
  const [panelOpen, setPanelOpen] = useState(false);
```

- [ ] **Step 2: Add `addTag` and `removeTag` handlers**

Add these two functions inside `JobCard`, after the state declarations and before the `location` const:

```tsx
  const addTag = async (tag: Tag) => {
    await fetch(`${API}/api/jobs/${job.id}/tags/${tag.id}`, { method: "POST" });
    setTags((prev) => [...prev, tag]);
    setPanelOpen(false);
  };

  const removeTag = async (tag: Tag) => {
    await fetch(`${API}/api/jobs/${job.id}/tags/${tag.id}`, { method: "DELETE" });
    setTags((prev) => prev.filter((t) => t.id !== tag.id));
  };

  const appliedIds = new Set(tags.map((t) => t.id));
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/JobCard.tsx
git commit -m "feat(tags): convert JobCard to client component with tag state"
```

---

### Task 3: Replace the "Interested" badge with a full tag chip row and quick-add panel

**Files:**
- Modify: `frontend/components/JobCard.tsx`

- [ ] **Step 1: Replace the badge block and add the tag row + panel**

In `frontend/components/JobCard.tsx`, find and remove the entire `<div className="flex shrink-0 gap-1.5">` block (the one containing the Reposted badge and Interested badge):

```tsx
        <div className="flex shrink-0 gap-1.5">
          {job.is_repost && (
            <span className="text-xs font-semibold px-2 py-1 rounded-full bg-accent/20 text-accent border border-accent/40">
              Reposted
            </span>
          )}
          {job.tags?.some((t) => t.name.toLowerCase() === "interested") && (
            <span className="text-xs font-semibold px-2 py-1 rounded-full bg-primary/15 text-primary border border-primary/30">
              Interested
            </span>
          )}
        </div>
```

Replace it with just the Reposted badge (keep it in the header, no Interested special-case):

```tsx
        {job.is_repost && (
          <span className="shrink-0 text-xs font-semibold px-2 py-1 rounded-full bg-accent/20 text-accent border border-accent/40">
            Reposted
          </span>
        )}
```

- [ ] **Step 2: Add the tag chip row with `+` button**

Find the existing listed-dates row:

```tsx
      <div className="mt-3 flex flex-wrap gap-1">
        {job.listed_dates.map((d) => (
          <span key={d} className="text-xs bg-gray-100 text-muted px-2 py-0.5 rounded">
            {d}
          </span>
        ))}
      </div>
```

Insert the tag row and panel **above** the dates row:

```tsx
      {/* Tag chip row */}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {tags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20"
          >
            {tag.name}
            <button
              onClick={() => removeTag(tag)}
              className="ml-0.5 hover:text-red-500 transition-colors leading-none"
              aria-label={`Remove ${tag.name}`}
            >
              &times;
            </button>
          </span>
        ))}
        <button
          onClick={() => setPanelOpen((o) => !o)}
          aria-label="Add tag"
          className={`w-5 h-5 rounded-full border text-sm flex items-center justify-center transition-colors ${
            panelOpen
              ? "border-primary bg-primary/10 text-primary"
              : "border-gray-300 text-muted hover:border-primary hover:text-primary"
          }`}
        >
          +
        </button>
      </div>

      {/* Quick-add panel */}
      {panelOpen && (
        <div className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
            All tags — click to add or remove
          </p>
          <div className="flex flex-wrap gap-1.5">
            {allTags.map((tag) =>
              appliedIds.has(tag.id) ? (
                <button
                  key={tag.id}
                  onClick={() => removeTag(tag)}
                  className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20 hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-colors"
                >
                  {tag.name} &times;
                </button>
              ) : (
                <button
                  key={tag.id}
                  onClick={() => addTag(tag)}
                  className="text-xs px-2.5 py-1 rounded-full bg-white text-gray-500 border border-gray-200 hover:border-primary hover:text-primary transition-colors"
                >
                  {tag.name}
                </button>
              )
            )}
          </div>
        </div>
      )}
```

- [ ] **Step 3: Verify TypeScript compiles with no errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Verify ESLint is clean**

```bash
cd frontend && npx eslint components/JobCard.tsx
```

Expected: no errors or warnings.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/JobCard.tsx
git commit -m "feat(tags): add tag chip row and quick-add panel to JobCard"
```

---

### Task 4: Smoke test in the browser

- [ ] **Step 1: Start the app**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`.

- [ ] **Step 2: Verify tag chips render on listing cards**

Jobs that already have tags should show blue chips with `×`. Jobs with no tags show only the `+` button.

- [ ] **Step 3: Verify the quick-add panel opens and closes**

Click `+` on a card — panel opens showing all tags. Applied tags are blue, unapplied are gray. Click `+` again — panel closes.

- [ ] **Step 4: Verify adding a tag**

Click an unapplied (gray) tag in the panel. The tag should appear as a blue chip in the row and in the panel. Panel closes.

- [ ] **Step 5: Verify removing a tag from the row**

Click `×` on a tag chip in the row. Tag disappears from the row immediately.

- [ ] **Step 6: Verify removing a tag from the panel**

Open the panel, click a blue (applied) tag — it should disappear from both the panel chips and the card row.

- [ ] **Step 7: Verify the detail page is unaffected**

Navigate to any job detail page (`/jobs/{id}`). `TagManager` should still work exactly as before.
