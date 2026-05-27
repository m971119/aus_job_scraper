"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { JobsPage, Tag } from "@/types";
import JobCard from "./JobCard";
import TagMultiSelect from "./TagMultiSelect";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PAGE_SIZE_OPTIONS = [10, 25, 50];

interface Props {
  refreshKey: number;
  onFilterStateChange?: (hasFilters: boolean, reset: () => void) => void;
}

export default function JobList({ refreshKey, onFilterStateChange }: Props) {
  const searchParams = useSearchParams();

  const [keyword, setKeyword] = useState(searchParams.get("keyword") ?? "");
  const [location, setLocation] = useState(searchParams.get("location") ?? "");
  const [includeTags, setIncludeTags] = useState<string[]>(searchParams.getAll("include_tag"));
  const [excludeTags, setExcludeTags] = useState<string[]>(searchParams.getAll("exclude_tag"));
  const [isRepost, setIsRepost] = useState<"all" | "originals" | "reposts">(
    (searchParams.get("is_repost") as "all" | "originals" | "reposts") ?? "all"
  );
  const [sort, setSort] = useState<"latest" | "oldest">(
    (searchParams.get("sort") as "latest" | "oldest") ?? "latest"
  );
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [data, setData] = useState<JobsPage>({ items: [], total: 0, page: 1, page_size: 25 });

  const hasActiveFilters = !!(keyword || location || includeTags.length || excludeTags.length || isRepost !== "all" || sort !== "latest");

  const resetFilters = useCallback(() => {
    setKeyword("");
    setLocation("");
    setIncludeTags([]);
    setExcludeTags([]);
    setIsRepost("all");
    setSort("latest");
  }, []);

  useEffect(() => {
    onFilterStateChange?.(hasActiveFilters, resetFilters);
  }, [hasActiveFilters, onFilterStateChange, resetFilters]);

  useEffect(() => {
    fetch(`${API}/api/tags`).then((r) => r.json()).then(setAllTags);
  }, []);

  // Sync filters to URL without triggering Next.js navigation
  useEffect(() => {
    const params = new URLSearchParams();
    if (keyword) params.set("keyword", keyword);
    if (location) params.set("location", location);
    includeTags.forEach((t) => params.append("include_tag", t));
    excludeTags.forEach((t) => params.append("exclude_tag", t));
    if (isRepost !== "all") params.set("is_repost", isRepost);
    if (sort !== "latest") params.set("sort", sort);
    const qs = params.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [keyword, location, includeTags, excludeTags, isRepost, sort]);

  const buildParams = useCallback((p: number) => {
    const params = new URLSearchParams({ sort, page: String(p), page_size: String(pageSize) });
    if (keyword) params.set("keyword", keyword);
    if (location) params.set("location", location);
    includeTags.forEach((t) => params.append("include_tag", t));
    excludeTags.forEach((t) => params.append("exclude_tag", t));
    if (isRepost !== "all") params.set("is_repost", isRepost);
    return params;
  }, [keyword, location, includeTags, excludeTags, isRepost, sort, pageSize]);

  // Reset page when filters change (not page itself)
  useEffect(() => {
    setPage(1);
  }, [keyword, location, includeTags, excludeTags, isRepost, sort, pageSize, refreshKey]);

  // Single fetch effect — AbortController cancels any in-flight request
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/jobs?${buildParams(page)}`, { signal: controller.signal })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d) setData(d); })
      .catch(() => {});
    return () => controller.abort();
  }, [page, buildParams, refreshKey]);

  const totalPages = Math.max(1, Math.ceil(data.total / pageSize));

  const handleHide = async (id: number) => {
    setData((prev) => ({ ...prev, items: prev.items.filter((j) => j.id !== id), total: prev.total - 1 }));
    await fetch(`${API}/api/jobs/${id}/hide`, { method: "PATCH" });
  };

  return (
    <div>
      <div className="flex flex-col gap-3 mb-4">
        <div className="flex gap-3">
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
        </div>
        <div className="grid grid-cols-4 gap-3">
          <TagMultiSelect
            label="Include tags"
            tags={allTags}
            selected={includeTags}
            onChange={setIncludeTags}
          />
          <TagMultiSelect
            label="Exclude tags"
            tags={allTags}
            selected={excludeTags}
            onChange={setExcludeTags}
          />
          <select
            value={isRepost}
            onChange={(e) => setIsRepost(e.target.value as "all" | "originals" | "reposts")}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
          >
            <option value="all">All jobs</option>
            <option value="originals">Originals only</option>
            <option value="reposts">Reposts only</option>
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as "latest" | "oldest")}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm bg-white text-gray-700"
          >
            <option value="latest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>
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
            <JobCard key={job.id} job={job} allTags={allTags} onHide={handleHide} />
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
