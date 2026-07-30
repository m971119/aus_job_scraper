"use client";
import { useEffect, useRef, useState } from "react";
import { AiFilterStatus } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ACTIVE_STATUSES = new Set(["uploading", "submitted"]);

export default function AiFilterPage() {
  const [filterStatus, setFilterStatus] = useState<AiFilterStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = async (): Promise<AiFilterStatus> => {
    const r = await fetch(`${API}/api/ai-filter/status`);
    const data: AiFilterStatus = await r.json();
    setFilterStatus(data);
    return data;
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = () => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const data = await fetchStatus();
      if (!ACTIVE_STATUSES.has(data.status)) stopPolling();
    }, 2000);
  };

  useEffect(() => {
    fetchStatus().then((data) => {
      if (ACTIVE_STATUSES.has(data.status)) startPolling();
    });
    return () => stopPolling();
  }, []);

  const handleRun = async () => {
    await fetch(`${API}/api/ai-filter/run`, { method: "POST" });
    await fetchStatus();
    startPolling();
  };

  const handleCancel = async () => {
    await fetch(`${API}/api/ai-filter/cancel`, { method: "POST" });
  };

  const isActive = ACTIVE_STATUSES.has(filterStatus?.status ?? "");
  const progress =
    filterStatus && filterStatus.total_jobs > 0
      ? Math.round((filterStatus.completed / filterStatus.total_jobs) * 100)
      : 0;

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <div className="h-1 w-12 bg-accent rounded mb-6" />
      <h1 className="text-2xl font-bold text-navy mb-2">AI Job Filter</h1>
      <p className="text-sm text-muted mb-8">
        Automatically hides jobs that clearly do not match a software engineering role — e.g. civil
        engineers, ASP.NET-only roles, and leadership positions.
      </p>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-5">
        <div className="flex items-center gap-3">
          <button
            onClick={handleRun}
            disabled={isActive}
            className="bg-secondary text-white text-sm font-semibold px-4 py-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isActive ? "Running..." : "Run Filter"}
          </button>
          {isActive && (
            <button
              onClick={handleCancel}
              className="text-sm text-muted hover:text-red-500 transition-colors px-3 py-2 rounded-lg hover:bg-red-50"
            >
              Cancel
            </button>
          )}
        </div>

        {filterStatus && filterStatus.status !== "idle" && (
          <div className="space-y-3">
            {filterStatus.status === "uploading" && (
              <p className="text-sm text-muted">Uploading jobs to OpenAI...</p>
            )}

            {filterStatus.status === "submitted" && (
              <div>
                <div className="flex justify-between text-xs text-muted mb-1.5">
                  <span>
                    {filterStatus.completed} / {filterStatus.total_jobs} processed
                  </span>
                  <span>{filterStatus.hidden} hidden</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                {filterStatus.batch_id && (
                  <p className="text-xs text-muted mt-1.5">
                    Batch ID: {filterStatus.batch_id}
                  </p>
                )}
              </div>
            )}

            {filterStatus.status === "done" && (
              <p className="text-sm text-gray-700">
                Done &mdash;{" "}
                <span className="font-semibold text-navy">{filterStatus.hidden}</span> jobs hidden
                out of{" "}
                <span className="font-semibold text-navy">{filterStatus.total_jobs}</span> evaluated.
              </p>
            )}

            {filterStatus.status === "cancelled" && (
              <p className="text-sm text-muted">
                Cancelled &mdash; {filterStatus.hidden} jobs hidden before cancellation.
              </p>
            )}

            {filterStatus.status === "error" && (
              <p className="text-sm text-red-500">Error: {filterStatus.error}</p>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
