"use client";
import { useState, useEffect, useCallback } from "react";
import { JobsPage } from "@/types";
import JobCard from "./JobCard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PAGE_SIZE_OPTIONS = [10, 25, 50];

interface Props {
  refreshKey: number;
}

export default function JobList({ refreshKey }: Props) {
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [sort, setSort] = useState<"latest" | "oldest">("latest");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [data, setData] = useState<JobsPage>({ items: [], total: 0, page: 1, page_size: 25 });

  const fetchJobs = useCallback(async (p: number) => {
    const params = new URLSearchParams({ sort, page: String(p), page_size: String(pageSize) });
    if (keyword) params.set("keyword", keyword);
    if (location) params.set("location", location);
    const res = await fetch(`${API}/api/jobs?${params}`);
    if (res.ok) setData(await res.json());
  }, [keyword, location, sort, pageSize]);

  useEffect(() => {
    setPage(1);
    fetchJobs(1);
  }, [keyword, location, sort, pageSize, refreshKey, fetchJobs]);

  useEffect(() => {
    fetchJobs(page);
  }, [page, fetchJobs]);

  const totalPages = Math.max(1, Math.ceil(data.total / pageSize));

  const handleHide = async (id: number) => {
    setData((prev) => ({ ...prev, items: prev.items.filter((j) => j.id !== id), total: prev.total - 1 }));
    await fetch(`${API}/api/jobs/${id}/hide`, { method: "PATCH" });
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <input
          type="text"
          placeholder="Filter by keyword..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
        />
        <input
          type="text"
          placeholder="Filter by location..."
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as "latest" | "oldest")}
          className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
        >
          <option value="latest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
      </div>

      <div className="flex items-center justify-between mb-4 text-xs text-muted">
        <span>{data.total} job{data.total !== 1 ? "s" : ""} found</span>
        <div className="flex items-center gap-2">
          <span>Per page</span>
          <select
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            className="px-2 py-1 border border-gray-200 rounded text-xs bg-white text-gray-700"
          >
            {PAGE_SIZE_OPTIONS.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      {data.items.length === 0 ? (
        <p className="text-muted text-center py-12">No jobs found.</p>
      ) : (
        <div className="grid gap-4">
          {data.items.map((job) => (
            <JobCard key={job.id} job={job} onHide={handleHide} />
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
    </div>
  );
}
