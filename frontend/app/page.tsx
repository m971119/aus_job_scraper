"use client";
import { useState, useEffect, useCallback } from "react";
import SearchForm from "@/components/SearchForm";
import JobList from "@/components/JobList";
import { Job } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scrapeMsg, setScrapeMsg] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    const res = await fetch(`${API}/api/jobs`);
    if (res.ok) setJobs(await res.json());
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleScrape = async (keywords: string, location: string) => {
    setLoading(true);
    setError(null);
    setScrapeMsg(null);
    try {
      const res = await fetch(`${API}/api/scrape`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords, location, max_pages: 3 }),
      });
      if (!res.ok) throw new Error(`Scrape failed: ${res.status}`);
      const data = await res.json();
      setScrapeMsg(`Done — ${data.inserted} new, ${data.updated_reposts} reposted`);
      await fetchJobs();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-8">
        <div className="h-1 w-16 bg-accent rounded mb-4" />
        <h1 className="text-3xl font-bold text-navy">Aus Job Scraper</h1>
        <p className="text-muted mt-1">Search and scrape recent jobs from Seek.com.au</p>
      </div>

      <div className="p-5 bg-white rounded-xl border border-gray-100 shadow-sm">
        <SearchForm onScrape={handleScrape} loading={loading} />
        {error && <p className="mt-3 text-red-500 text-sm">{error}</p>}
        {scrapeMsg && <p className="mt-3 text-green-600 text-sm">{scrapeMsg}</p>}
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold text-navy mb-4">
          Saved Jobs ({jobs.length})
        </h2>
        <JobList jobs={jobs} />
      </div>
    </main>
  );
}
