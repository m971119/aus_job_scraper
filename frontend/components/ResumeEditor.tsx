"use client";
import { useState, useEffect, useRef } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { html } from "@codemirror/lang-html";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const A4_HEIGHT_PX = 1122;

interface VersionMeta {
  id: number;
  label: string;
  created_at: string;
}

export default function ResumeEditor() {
  const [content, setContent] = useState("");
  const [debouncedContent, setDebouncedContent] = useState("");
  const [label, setLabel] = useState("");
  const [versions, setVersions] = useState<VersionMeta[]>([]);
  const [selectedId, setSelectedId] = useState<number | "">("");
  const [overflow, setOverflow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    fetch(`${API}/api/resume/versions`)
      .then((r) => r.json())
      .then(setVersions);
    fetch(`${API}/api/resume`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) {
          setContent(d.content);
          setDebouncedContent(d.content);
          setSelectedId(d.id);
        }
      });
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedContent(content), 300);
    return () => clearTimeout(t);
  }, [content]);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    const onLoad = () => {
      const h = iframe.contentDocument?.documentElement?.scrollHeight ?? 0;
      setOverflow(h > A4_HEIGHT_PX);
    };
    iframe.addEventListener("load", onLoad);
    return () => iframe.removeEventListener("load", onLoad);
  }, []);

  const loadVersion = async (id: number) => {
    const resp = await fetch(`${API}/api/resume/versions/${id}`);
    const d = await resp.json();
    setContent(d.content);
    setDebouncedContent(d.content);
    setSelectedId(d.id);
  };

  const handleSave = async () => {
    if (!label.trim() || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const resp = await fetch(`${API}/api/resume/versions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: label.trim(), content }),
      });
      if (!resp.ok) throw new Error(`Save failed: ${resp.status}`);
      const v = await resp.json();
      setVersions((prev) => [v, ...prev]);
      setSelectedId(v.id);
      setLabel("");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handlePrint = () => {
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(content);
    win.document.close();
    win.focus();
    win.onload = () => win.print();
  };

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 56px)" }}>
      {/* Split pane */}
      <div className="flex flex-1 min-h-0">
        {/* Left: code editor */}
        <div className="w-[45%] border-r border-gray-200 overflow-hidden">
          <CodeMirror
            value={content}
            height="calc(100vh - 113px)"
            extensions={[html()]}
            onChange={setContent}
            style={{ fontSize: "13px" }}
          />
        </div>

        {/* Right: A4 preview */}
        <div className="flex-1 overflow-auto bg-gray-50 p-6 flex flex-col items-center">
          <div
            className={`bg-white shadow-md ${overflow ? "ring-2 ring-red-500" : ""}`}
            style={{ width: "210mm" }}
          >
            <iframe
              ref={iframeRef}
              srcDoc={debouncedContent}
              style={{
                width: "210mm",
                height: "297mm",
                border: "none",
                display: "block",
              }}
              sandbox="allow-same-origin"
              title="Resume preview"
            />
          </div>
          {overflow && (
            <p className="mt-2 text-xs font-semibold text-red-500">
              Content overflows A4 — reduce content or font size
            </p>
          )}
        </div>
      </div>

      {/* Bottom toolbar */}
      <div className="border-t border-gray-200 bg-white px-4 py-3 flex items-center gap-3 shrink-0">
        <select
          value={selectedId}
          onChange={(e) => loadVersion(Number(e.target.value))}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary max-w-xs"
        >
          <option value="" disabled>
            Version history
          </option>
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              {v.label} — {new Date(v.created_at).toLocaleDateString()}
            </option>
          ))}
        </select>
        <div className="flex-1" />
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
          }}
          placeholder="Version label..."
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 w-48 focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {saveError && (
          <span className="text-xs text-red-500">{saveError}</span>
        )}
        <button
          onClick={handleSave}
          disabled={!label.trim() || saving}
          className="text-sm font-semibold bg-secondary text-white px-4 py-1.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          onClick={handlePrint}
          className="text-sm font-semibold border border-primary text-primary px-4 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-colors"
        >
          Print
        </button>
      </div>
    </div>
  );
}
