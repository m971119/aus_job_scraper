# Cover Letter Notes-Style Editor & PDF Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the job detail page's cover letter editor to match the Notes panel's click-to-edit UX, and add a "Download PDF" button that exports the letter as a resume-styled, print-ready document with the candidate's name and contact details.

**Architecture:** Frontend-only change. A new pure-function module builds a standalone HTML document (reusing the resume's header CSS) and opens it in a new tab via `window.print()` — the same pattern the Resume page already uses for its own PDF export. The cover letter's content editor swaps its always-visible textarea for a view/edit toggle matching `NotesEditor.tsx`.

**Tech Stack:** Next.js (client components), TypeScript, native `DOMParser` (no new dependency), Tailwind CSS.

## Global Constraints

- Backend, DB, and API routes are untouched — `CoverLetterOut.resume_version_id` and `GET /api/resume/versions/{id}` already exist and already provide everything needed.
- No new npm dependencies.
- No automated frontend test suite exists in this project (no jest/vitest config, no `.test.ts` files) — verification is `npx tsc --noEmit`, `npm run build`, and manual browser checks, matching existing project convention.
- Cover letter content stays plain text (not HTML/rich text) — the AI generate/chat flow in `backend/routes/ai.py` reads and writes plain text and is not being changed.

---

## Task 1: Cover letter PDF template + export utility

**Files:**
- Modify: `frontend/types.ts`
- Create: `frontend/lib/coverLetterPdf.ts`

**Interfaces:**
- Consumes: nothing from other tasks (this is the foundation task)
- Produces: `openCoverLetterPdf(params: { resumeVersionId: number; company: string | null; title: string; seekUrl: string; content: string }): Promise<void>` — fetches the resume, builds the letter HTML, opens a new tab and calls `window.print()`. Throws an `Error` with a user-facing message if the resume fetch fails or the pop-up is blocked, for the caller (Task 2) to catch and display.
- Produces (for direct testing): `buildCoverLetterHtml(params: { name: string; contactHtml: string; company: string | null; title: string; seekUrl: string; content: string }): string`

- [ ] **Step 1: Add the `ResumeVersionOut` type**

In `frontend/types.ts`, after the `ResumeVersionMeta` interface (end of file, currently lines 92-96), add:

```typescript
export interface ResumeVersionOut {
  id: number;
  label: string;
  content: string;
  created_at: string;
}
```

- [ ] **Step 2: Create `frontend/lib/coverLetterPdf.ts`**

```typescript
import { ResumeVersionOut } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

interface CoverLetterHtmlParams {
  name: string;
  contactHtml: string;
  company: string | null;
  title: string;
  seekUrl: string;
  content: string;
}

export function buildCoverLetterHtml({
  name,
  contactHtml,
  company,
  title,
  seekUrl,
  content,
}: CoverLetterHtmlParams): string {
  const date = new Date().toLocaleDateString("en-AU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const salutation = company
    ? `Dear ${escapeHtml(company)} Hiring Team,`
    : "Dear Hiring Manager,";
  const paragraphs = content
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${escapeHtml(p)}</p>`)
    .join("\n");

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>${escapeHtml(name)} — Cover Letter</title>
<style>
  @page { size: A4; margin: 1.4cm 2.2cm; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Times New Roman", Times, serif;
    font-size: 11pt;
    color: #000;
    background: #fff;
    max-width: 720px;
    margin: 24px auto;
    padding: 0 64px 36px;
    line-height: 1.5;
  }
  @media print {
    body { margin: 0; padding: 0; max-width: 100%; }
  }
  h1 { text-align: center; font-size: 20pt; font-weight: bold; margin-bottom: 3px; }
  .contact { text-align: center; font-size: 9.5pt; margin-bottom: 10px; }
  .contact a { color: #000; text-decoration: none; }
  .divider { border: none; border-top: 0.75pt solid #000; margin: 0 0 18px; }
  .date { margin-bottom: 16px; }
  .reference { margin-bottom: 16px; }
  .reference a { color: #000; }
  .salutation { margin-bottom: 12px; }
  .body p { margin-bottom: 12px; text-align: justify; }
  .signoff { margin-top: 16px; }
</style>
</head>
<body>
  <h1>${escapeHtml(name)}</h1>
  <p class="contact">${contactHtml}</p>
  <hr class="divider" />
  <p class="date">${date}</p>
  <p class="reference">Re: <a href="${escapeHtml(seekUrl)}">${escapeHtml(title)}</a></p>
  <p class="salutation">${salutation}</p>
  <div class="body">${paragraphs}</div>
  <p class="signoff">Sincerely,<br />${escapeHtml(name)}</p>
</body>
</html>`;
}

interface OpenCoverLetterPdfParams {
  resumeVersionId: number;
  company: string | null;
  title: string;
  seekUrl: string;
  content: string;
}

export async function openCoverLetterPdf({
  resumeVersionId,
  company,
  title,
  seekUrl,
  content,
}: OpenCoverLetterPdfParams): Promise<void> {
  const resp = await fetch(`${API}/api/resume/versions/${resumeVersionId}`);
  if (!resp.ok) throw new Error("Could not load resume for contact details");
  const resume: ResumeVersionOut = await resp.json();

  const doc = new DOMParser().parseFromString(resume.content, "text/html");
  const name = doc.querySelector("h1")?.textContent?.trim() ?? "";
  const contactHtml = doc.querySelector(".contact")?.innerHTML ?? "";

  const html = buildCoverLetterHtml({ name, contactHtml, company, title, seekUrl, content });

  const win = window.open("", "_blank");
  if (!win) throw new Error("Pop-up blocked — allow pop-ups to download the PDF");
  win.document.open();
  win.document.write(html);
  win.document.close();
  win.focus();
  win.print();
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors referencing `types.ts` or `lib/coverLetterPdf.ts`.

- [ ] **Step 4: Sanity-check the HTML builder in the Node REPL**

Run:
```bash
cd frontend && npx tsx -e '
import { buildCoverLetterHtml } from "./lib/coverLetterPdf";
const html = buildCoverLetterHtml({
  name: "Michelle Lin",
  contactHtml: "<a href=\"mailto:test@example.com\">test@example.com</a>",
  company: "Acme & Co",
  title: "Backend Engineer",
  seekUrl: "/job/12345",
  content: "Paragraph one.\n\nParagraph two with <b>tag</b>.",
});
console.log(html.includes("Dear Acme &amp; Co Hiring Team,"));
console.log(html.includes("<p>Paragraph one.</p>"));
console.log(html.includes("&lt;b&gt;tag&lt;/b&gt;"));
console.log(html.includes(`Re: <a href="/job/12345">Backend Engineer</a>`));
'
```
Expected: four lines printed, all `true` — confirms company-name escaping in the salutation, paragraph splitting, content escaping, and the job reference link all work.

If `tsx` isn't available, run `cd frontend && npx --yes tsx -e '...'` (same command) — `npx --yes` will fetch it for this one-off check without adding it as a project dependency.

- [ ] **Step 5: Commit**

```bash
git add frontend/types.ts frontend/lib/coverLetterPdf.ts
git commit -m "feat(cover-letter): add pdf export template utility"
```

---

## Task 2: Notes-style editor and Download PDF button in `CoverLetter.tsx`

**Files:**
- Modify: `frontend/components/CoverLetter.tsx`

**Interfaces:**
- Consumes: `openCoverLetterPdf` from `frontend/lib/coverLetterPdf.ts` (Task 1)
- Produces: `CoverLetter` component now accepts additional `company?: string | null`, `title: string`, and `seekUrl: string` props (used by Task 3)

- [ ] **Step 1: Add the import and new props**

In `frontend/components/CoverLetter.tsx`, add near the top imports (after the existing `ModelPicker` import on line 4):

```typescript
import { openCoverLetterPdf } from "@/lib/coverLetterPdf";
```

Change the `Props` interface (currently lines 8-10):

```typescript
interface Props {
  jobId: number;
  company?: string | null;
  title: string;
  seekUrl: string;
}
```

Change the component signature (currently line 35 `export default function CoverLetter({ jobId }: Props) {`):

```typescript
export default function CoverLetter({ jobId, company, title, seekUrl }: Props) {
```

- [ ] **Step 2: Add `editing` state and the PDF download handler**

Add a new state line next to the existing `open` state (currently line 44 `const [open, setOpen] = useState(false);`):

```typescript
const [editing, setEditing] = useState(false);
```

Add a new handler after `handleSaveEdit` (currently lines 126-132):

```typescript
const handleDownloadPdf = async () => {
  if (!cl) return;
  try {
    await openCoverLetterPdf({
      resumeVersionId: cl.resume_version_id,
      company: company ?? null,
      title,
      seekUrl,
      content,
    });
  } catch (e) {
    setError(e instanceof Error ? e.message : "PDF export failed");
  }
};
```

- [ ] **Step 3: Replace the always-visible textarea with a view/edit toggle**

Replace this block (currently lines 163-181):

```typescript
          {(content || streamBuffer) && (
            <>
              <textarea
                value={streaming ? streamBuffer : content}
                onChange={(e) => setContent(e.target.value)}
                readOnly={streaming}
                rows={10}
                className="w-full text-sm border border-gray-200 rounded-lg p-3 font-mono resize-y focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {!streaming && (
                <button
                  onClick={handleSaveEdit}
                  className="text-xs text-primary hover:underline"
                >
                  Save edits
                </button>
              )}
            </>
          )}
```

with:

```typescript
          {(content || streamBuffer) && (
            <>
              {streaming ? (
                <div className="px-3 py-2.5 border border-gray-200 rounded-lg bg-gray-50 text-sm whitespace-pre-wrap leading-relaxed">
                  {streamBuffer}
                </div>
              ) : editing ? (
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  onBlur={() => {
                    handleSaveEdit();
                    setEditing(false);
                  }}
                  rows={10}
                  autoFocus
                  className="w-full text-sm border border-primary rounded-lg p-3 resize-y focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              ) : (
                <div
                  onClick={() => setEditing(true)}
                  className="cursor-pointer px-3 py-2.5 border border-gray-200 rounded-lg bg-gray-50 text-sm whitespace-pre-wrap leading-relaxed hover:border-primary/40 transition-colors"
                >
                  {content}
                </div>
              )}
            </>
          )}
```

- [ ] **Step 4: Add the Download PDF button**

Replace the button row (currently lines 148-161):

```typescript
          <div className="flex items-center gap-2">
            <ModelPicker value={model} onChange={setModel} disabled={streaming} />
            <button
              onClick={handleGenerate}
              disabled={streaming}
              className="text-xs font-semibold bg-secondary text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              {streaming && messages.length === 0
                ? "Generating..."
                : cl
                ? "Regenerate"
                : "Generate"}
            </button>
          </div>
```

with:

```typescript
          <div className="flex items-center gap-2">
            <ModelPicker value={model} onChange={setModel} disabled={streaming} />
            <button
              onClick={handleGenerate}
              disabled={streaming}
              className="text-xs font-semibold bg-secondary text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              {streaming && messages.length === 0
                ? "Generating..."
                : cl
                ? "Regenerate"
                : "Generate"}
            </button>
            {cl && (
              <button
                onClick={handleDownloadPdf}
                className="text-xs font-semibold border border-primary text-primary px-3 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-colors"
              >
                Download PDF
              </button>
            )}
          </div>
```

- [ ] **Step 5: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors in `components/CoverLetter.tsx`.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/CoverLetter.tsx
git commit -m "feat(cover-letter): notes-style editor and pdf download button"
```

---

## Task 3: Wire `company`/`title`/`seekUrl` props into the job detail page and verify end-to-end

**Files:**
- Modify: `frontend/app/jobs/[id]/page.tsx`

**Interfaces:**
- Consumes: `CoverLetter` component's `company?: string | null`, `title: string`, `seekUrl: string` props (Task 2)

- [ ] **Step 1: Pass the new props to `CoverLetter`**

In `frontend/app/jobs/[id]/page.tsx`, change line 230:

```typescript
        <CoverLetter jobId={job.id} />
```

to:

```typescript
        <CoverLetter
          jobId={job.id}
          company={job.company}
          title={job.title}
          seekUrl={job.seek_url}
        />
```

- [ ] **Step 2: Verify the production build succeeds**

Run: `cd frontend && npm run build 2>&1 | tail -30`
Expected: build completes with no type errors.

- [ ] **Step 3: Manual browser verification**

Run: `cd frontend && npm run dev` (and ensure the backend is running per `scripts/` for your OS)

In the browser, open a job detail page that has a description (needed for cover letter generation) and:
1. Expand the "Cover Letter" panel and click Generate. Confirm the letter streams in, then settles into a **view-mode box** (not a textarea) once done.
2. Click the letter text. Confirm it switches to an editable textarea, autofocused.
3. Edit the text and click elsewhere (blur). Confirm it returns to view mode showing the edited text, and reload the page to confirm the edit persisted (calls the existing `PATCH /cover-letter` endpoint).
4. Click "Download PDF". Confirm a new tab opens showing a print preview with: the resume's name centered at top in the same serif header style, the contact line with working `mailto:`/link styling, a horizontal rule under the contact line, today's date, a "Re:" line with the job title linked to its Seek URL, a salutation using the job's company name (or "Dear Hiring Manager," if the job has no company), the letter body as separate paragraphs, and a "Sincerely," sign-off with the name.
5. On a job with no linked resume version and no resume ever created, confirm clicking Download PDF shows an error message in the panel rather than a blank/broken print tab (this exercises the `!resp.ok` throw in `openCoverLetterPdf`).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/jobs/\[id\]/page.tsx
git commit -m "feat(cover-letter): pass job details into cover letter panel"
```

---

## Self-Review

| Spec requirement | Task |
|---|---|
| Notes-style click-to-edit view/edit toggle, plain text, saves on blur | Task 2 |
| AI generate/chat flow untouched (plain text content) | Task 2 (no changes to `handleGenerate`/`handleChat`/backend) |
| Download PDF button, enabled once `cl` exists | Task 2 |
| Fetch resume via `cl.resume_version_id` | Task 1, 2 |
| Parse name/contact via native `DOMParser` | Task 1 |
| Resume-styled HTML template (Times New Roman, A4, centered header) | Task 1 |
| Date, company-aware salutation, paragraph body, sign-off | Task 1 |
| Contact/body divider | Task 1 |
| "Re:" job reference line linked to `job.seek_url` | Task 1 |
| Open new tab + `window.print()` (browser Save-as-PDF) | Task 1 |
| Error shown in panel if resume fetch fails, no blank print window | Task 1 (throws), Task 2 (catches into `error` state), Task 3 Step 3.5 (manual check) |
| `company`/`title`/`seekUrl` props wired from job detail page | Task 3 |
