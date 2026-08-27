"use client";
import { useEffect, useRef, useState } from "react";
import { CoverLetterOut, MessageOut } from "@/types";
import ModelPicker from "./ModelPicker";
import { openCoverLetterPdf } from "@/lib/coverLetterPdf";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  jobId: number;
  company?: string | null;
  title: string;
  seekUrl: string;
}

async function readSSE(
  resp: Response,
  onChunk: (delta: string) => void,
  onDone: () => void
) {
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      if (!part.startsWith("data: ")) continue;
      const data = part.slice(6);
      if (data === "[DONE]") { onDone(); return; }
      try { onChunk(JSON.parse(data).delta); } catch { /* skip */ }
    }
  }
}

export default function CoverLetter({ jobId, company, title, seekUrl }: Props) {
  const [cl, setCl] = useState<CoverLetterOut | null>(null);
  const [content, setContent] = useState("");
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [model, setModel] = useState("gpt-4o-mini");
  const [chatInput, setChatInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    fetch(`${API}/api/jobs/${jobId}/cover-letter`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: CoverLetterOut | null) => {
        if (d) { setCl(d); setContent(d.content); setMessages(d.messages); }
      });
  }, [jobId, open]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer]);

  const handleGenerate = async () => {
    setError(null);
    setStreaming(true);
    setStreamBuffer("");
    const resp = await fetch(`${API}/api/jobs/${jobId}/cover-letter/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    if (!resp.ok) {
      const e = await resp.json();
      setError(e.detail ?? "Generation failed");
      setStreaming(false);
      return;
    }
    let full = "";
    await readSSE(
      resp,
      (delta) => { full += delta; setStreamBuffer(full); },
      () => {
        setContent(full);
        setStreamBuffer("");
        setStreaming(false);
        fetch(`${API}/api/jobs/${jobId}/cover-letter`)
          .then((r) => r.json())
          .then((d: CoverLetterOut) => { setCl(d); setMessages(d.messages); });
      }
    );
  };

  const handleChat = async () => {
    if (!chatInput.trim() || streaming) return;
    const msg = chatInput.trim();
    setChatInput("");
    setStreaming(true);
    setStreamBuffer("");
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", content: msg, created_at: "" },
    ]);
    const resp = await fetch(`${API}/api/jobs/${jobId}/cover-letter/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, model }),
    });
    if (!resp.ok) {
      setError("Chat failed");
      setStreaming(false);
      return;
    }
    let full = "";
    await readSSE(
      resp,
      (delta) => { full += delta; setStreamBuffer(full); },
      () => {
        setContent(full);
        setStreamBuffer("");
        setStreaming(false);
        setMessages((prev) => [
          ...prev,
          { id: Date.now() + 1, role: "assistant", content: full, created_at: "" },
        ]);
      }
    );
  };

  const handleSaveEdit = async () => {
    await fetch(`${API}/api/jobs/${jobId}/cover-letter`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
  };

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

  return (
    <div className="mt-6 border-t border-gray-100 pt-5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm font-semibold text-navy hover:text-primary transition-colors"
      >
        <span>Cover Letter</span>
        <span className="text-xs text-muted">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          {error && <p className="text-xs text-red-500">{error}</p>}

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

          {cl && (
            <>
              <div className="border border-gray-100 rounded-lg p-3 space-y-2 max-h-48 overflow-y-auto bg-gray-50">
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`text-xs ${m.role === "user" ? "text-muted" : "text-gray-800"}`}
                  >
                    <span className="font-semibold">
                      {m.role === "user" ? "You" : "AI"}:
                    </span>{" "}
                    {m.content}
                  </div>
                ))}
                {streamBuffer && (
                  <div className="text-xs text-gray-800">
                    <span className="font-semibold">AI:</span> {streamBuffer}
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleChat(); }}
                  placeholder="Ask for a revision..."
                  disabled={streaming}
                  className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                />
                <button
                  onClick={handleChat}
                  disabled={!chatInput.trim() || streaming}
                  className="text-xs font-semibold bg-secondary text-white px-3 py-1.5 rounded-lg hover:opacity-90 disabled:opacity-40"
                >
                  {streaming ? "..." : "Send"}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
