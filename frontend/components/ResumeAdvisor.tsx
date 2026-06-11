"use client";
import { useEffect, useRef, useState } from "react";
import { AdvisorOut, MessageOut } from "@/types";
import ModelPicker from "./ModelPicker";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TEMPLATE_PROMPTS = [
  "Please provide a structured analysis of my resume against this job description.",
  "What are the most critical gaps I need to address?",
  "Which parts of my resume should I emphasise most for this role?",
  "What should I remove or cut down?",
];

interface Props {
  jobId: number;
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

export default function ResumeAdvisor({ jobId }: Props) {
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [model, setModel] = useState("gpt-4o-mini");
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    fetch(`${API}/api/jobs/${jobId}/advisor`)
      .then((r) => r.json())
      .then((d: AdvisorOut | null) => {
        if (d) setMessages(d.messages);
      });
  }, [jobId, open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || streaming) return;
    setError(null);
    setInput("");
    setStreaming(true);
    setStreamBuffer("");
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", content: text, created_at: "" },
    ]);
    const resp = await fetch(`${API}/api/jobs/${jobId}/advisor/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, model }),
    });
    if (!resp.ok) {
      const e = await resp.json();
      setError(e.detail ?? "Request failed");
      setStreaming(false);
      return;
    }
    let full = "";
    await readSSE(
      resp,
      (delta) => { full += delta; setStreamBuffer(full); },
      () => {
        setStreamBuffer("");
        setStreaming(false);
        setMessages((prev) => [
          ...prev,
          { id: Date.now() + 1, role: "assistant", content: full, created_at: "" },
        ]);
      }
    );
  };

  return (
    <div className="mt-6 border-t border-gray-100 pt-5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm font-semibold text-navy hover:text-primary transition-colors"
      >
        <span>Resume Advisor</span>
        <span className="text-xs text-muted">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex items-center gap-2">
            <ModelPicker value={model} onChange={setModel} disabled={streaming} />
          </div>

          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2">
              {TEMPLATE_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  disabled={streaming}
                  className="text-xs border border-primary text-primary px-3 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-colors disabled:opacity-40"
                >
                  {p}
                </button>
              ))}
            </div>
          )}

          {(messages.length > 0 || streamBuffer) && (
            <div className="border border-gray-100 rounded-lg p-3 space-y-3 max-h-96 overflow-y-auto bg-gray-50">
              {messages.map((m) => (
                <div key={m.id} className={m.role === "user" ? "text-right" : "text-left"}>
                  <span
                    className={`inline-block text-xs px-3 py-2 rounded-lg whitespace-pre-wrap max-w-[85%] text-left ${
                      m.role === "user"
                        ? "bg-secondary text-white"
                        : "bg-white border border-gray-200 text-gray-800"
                    }`}
                  >
                    {m.content}
                  </span>
                </div>
              ))}
              {streamBuffer && (
                <div className="text-left">
                  <span className="inline-block text-xs px-3 py-2 rounded-lg bg-white border border-gray-200 text-gray-800 whitespace-pre-wrap max-w-[85%]">
                    {streamBuffer}
                  </span>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}

          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") sendMessage(input); }}
              placeholder="Ask the advisor..."
              disabled={streaming}
              className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || streaming}
              className="text-xs font-semibold bg-secondary text-white px-3 py-1.5 rounded-lg hover:opacity-90 disabled:opacity-40"
            >
              {streaming ? "..." : "Send"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
