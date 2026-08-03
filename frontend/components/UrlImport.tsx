"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function UrlImport() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingId, setExistingId] = useState<number | null>(null);

  const handleImport = async () => {
    if (!url.trim()) return;
    setError(null);
    setExistingId(null);
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/scrape/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!res.ok) {
        const e = await res.json();
        setError(e.detail ?? "Import failed");
        return;
      }
      const data: { exists: boolean; job_id: number } = await res.json();
      if (data.exists) {
        setExistingId(data.job_id);
      } else {
        router.push(`/jobs/${data.job_id}`);
      }
    } catch {
      setError("Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-5 bg-white rounded-xl border border-gray-100 shadow-sm">
      <h2 className="text-sm font-semibold text-navy mb-3">Import from URL</h2>
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => { setUrl(e.target.value); setExistingId(null); setError(null); }}
          onKeyDown={(e) => { if (e.key === "Enter") handleImport(); }}
          placeholder="https://www.seek.com.au/job/..."
          disabled={loading}
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        <button
          onClick={handleImport}
          disabled={!url.trim() || loading}
          className="text-xs font-semibold bg-secondary text-white px-3 py-1.5 rounded-lg hover:opacity-90 disabled:opacity-40"
        >
          {loading ? "Importing..." : "Import"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      {existingId && (
        <p className="mt-2 text-xs text-muted">
          This job already exists.{" "}
          <a href={`/jobs/${existingId}`} className="text-primary hover:underline">
            View job
          </a>
        </p>
      )}
    </div>
  );
}
