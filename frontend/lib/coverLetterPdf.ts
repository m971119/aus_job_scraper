import { ResumeVersionOut } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
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
