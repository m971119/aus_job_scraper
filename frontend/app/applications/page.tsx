"use client";
import { useState, useEffect, useCallback } from "react";
import { JobsPage, Tag, JobStatus } from "@/types";
import JobCard from "@/components/JobCard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PAGE_SIZE = 25;

type Tab = "ALL" | JobStatus;

const TABS: { value: Tab; label: string }[] = [
  { value: "ALL", label: "All" },
  { value: "APPLIED", label: "Applied" },
  { value: "INTERVIEWING", label: "Interviewing" },
  { value: "OFFER", label: "Offer" },
  { value: "ACCEPTED", label: "Accepted" },
  { value: "REJECTED", label: "Rejected" },
  { value: "WITHDRAWN", label: "Withdrawn" },
  { value: "GHOSTED", label: "Ghosted" },
];

export default function ApplicationsPage() {
  const [tab, setTab] = useState<Tab>("APPLIED");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<JobsPage>({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [sponsors, setSponsors] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API}/api/tags`).then((r) => r.json()).then(setAllTags);
    fetch(`${API}/api/sponsors`).then((r) => r.json()).then((d) => setSponsors(d.sponsors));
  }, []);

  useEffect(() => {
    setPage(1);
  }, [tab]);

  const buildParams = useCallback(
    (p: number) => {
      const params = new URLSearchParams({
        visibility: "visible",
        sort: "latest",
        page: String(p),
        page_size: String(PAGE_SIZE),
      });
      if (tab === "ALL") {
        params.set("not_saved", "true");
      } else {
        params.set("status", tab);
      }
      return params;
    },
    [tab]
  );

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/jobs?${buildParams(page)}`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) setData(d);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [page, buildParams]);

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  const handleHide = async (id: number) => {
    setData((prev) => ({
      ...prev,
      items: prev.items.filter((j) => j.id !== id),
      total: prev.total - 1,
    }));
    await fetch(`${API}/api/jobs/${id}/hide`, { method: "PATCH" });
  };

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-navy mb-6">Applications</h1>

      <div className="flex gap-0.5 overflow-x-auto pb-px mb-6 border-b border-gray-200">
        {TABS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`shrink-0 px-4 py-2 text-sm font-semibold transition-colors ${
              tab === value
                ? "text-primary border-b-2 border-primary -mb-px bg-primary/5"
                : "text-muted hover:text-navy"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between mb-4 text-xs text-muted">
        <span>
          {data.total} job{data.total !== 1 ? "s" : ""}
        </span>
      </div>

      {data.items.length === 0 ? (
        <p className="text-muted text-center py-12">No jobs found.</p>
      ) : (
        <div className="grid gap-4">
          {data.items.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              allTags={allTags}
              sponsors={sponsors}
              onHide={handleHide}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:border-primary hover:text-primary transition-colors"
          >
            &larr; Prev
          </button>
          <span className="text-sm text-muted px-2">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:border-primary hover:text-primary transition-colors"
          >
            Next &rarr;
          </button>
        </div>
      )}
    </main>
  );
}
