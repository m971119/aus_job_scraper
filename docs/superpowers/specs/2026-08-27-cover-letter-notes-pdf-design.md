# Cover Letter Notes-Style Editor & PDF Export

## Goal

The job detail page's cover letter panel currently shows an always-visible plain
textarea once a letter exists. Replace that with a click-to-edit view matching
the Notes panel's interaction pattern, and add a "Download PDF" button that
exports the letter as a resume-styled, print-ready document with the
candidate's name and contact details.

## Scope

Frontend only. The backend already exposes everything needed:
`CoverLetterOut.resume_version_id` identifies which resume version to source
contact details from, and `GET /api/resume/versions/{id}` returns that
resume's full HTML. No DB, schema, or route changes.

## 1. Editor UX

`CoverLetter.tsx`'s content block changes from an always-visible textarea to a
view/edit toggle, mirroring `NotesEditor.tsx`:

- **View mode**: content shown in a bordered box (`border-gray-200 rounded-lg
  bg-gray-50`), plain text rendered with `whitespace-pre-wrap` (paragraphs stay
  separated by the blank lines the AI already generates), click anywhere or an
  "Edit" button to enter edit mode.
- **Edit mode**: textarea, saves on blur via the existing `PATCH
  /api/jobs/{job_id}/cover-letter` endpoint (already implemented as
  `handleSaveEdit`), then returns to view mode.
- No rich text (Tiptap) — cover letters are prose paragraphs, not formatted
  notes. This keeps the stored `content` as plain text, so the AI
  generate/chat flow (which reads/writes plain text) is untouched.
- The AI generate/regenerate controls and chat revision panel stay as they are
  today; only the content display/edit block is restyled.

## 2. PDF Export

A "Download PDF" button sits next to Generate/Regenerate, enabled once a
cover letter exists (`cl !== null`). On click (`frontend/lib/coverLetterPdf.ts`):

1. Fetch resume HTML: `GET /api/resume/versions/{cl.resume_version_id}`.
2. Parse it with the browser's native `DOMParser` (no new dependency):
   - name = `doc.querySelector('h1')?.textContent`
   - contact = `doc.querySelector('.contact')?.innerHTML` (keeps the
     mailto/LinkedIn/GitHub anchors as in the resume)
3. Build a standalone HTML document reusing the resume's header styling
   (Times New Roman, A4 `@page`, centered name + contact line — same CSS
   values as `resume-updated.html`), plus letter-specific content:
   - A thin horizontal rule between the contact line and the date, separating
     the header from the letter body
   - Today's date
   - A reference line: `Re: {job title}`, with the title linked to the job's
     Seek URL (`job.seek_url`, used as-is — the app already treats it as a
     ready-to-use href elsewhere, e.g. the job detail page's "View on Seek"
     link)
   - Salutation: `Dear {company} Hiring Team,` if the job has a company,
     otherwise `Dear Hiring Manager,`
   - Body: `cl.content` split on blank lines, each paragraph escaped
     (`&`, `<`, `>`) and wrapped in `<p>`, justified text like the resume
   - Sign-off: `Sincerely,` followed by the parsed name
4. Open a new window, write the HTML, call `window.print()` — identical
   pattern to the Resume page's existing `handlePrint`, so "export to PDF" is
   the browser's native Save-as-PDF via the print dialog.

If the resume fetch fails (e.g. deleted version), show the existing `error`
state in the panel rather than opening a blank print window.

## 3. Files

- **New**: `frontend/lib/coverLetterPdf.ts` — `buildCoverLetterHtml(...)` and
  `openCoverLetterPdf(...)` (fetch resume, parse, build HTML, open + print)
- **Modify**: `frontend/components/CoverLetter.tsx` — view/edit toggle,
  Download PDF button, accepts new `company?: string` (salutation), `title:
  string` and `seekUrl: string` (reference line) props
- **Modify**: `frontend/app/jobs/[id]/page.tsx` — pass `company={job.company}`,
  `title={job.title}`, `seekUrl={job.seek_url}` to `<CoverLetter />`

## Testing

No automated frontend test suite exists in this project (no jest/playwright
test files). Verify manually with the dev server: generate a cover letter,
confirm the Notes-style view/edit toggle saves correctly, click Download PDF,
confirm the print preview shows name/contact/date/salutation/body/sign-off
correctly formatted, and confirm the print window doesn't open when there's
no resume version to source contact details from.
