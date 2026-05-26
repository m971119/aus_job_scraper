"use client";
import { useState, useEffect, useRef } from "react";
import SearchForm from "@/components/SearchForm";
import JobList from "@/components/JobList";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ScrapeStatus {
  status: string;
  phase: string;
  current_page: number;
  jobs_scraped: number;
  jobs_compared: number;
  inserted: number;
  updated_reposts: number;
  skipped_hidden: number;
  error: string | null;
}

const IDLE_STATUS: ScrapeStatus = {
  status: "idle",
  phase: "seeking",
  current_page: 0,
  jobs_scraped: 0,
  jobs_compared: 0,
  inserted: 0,
  updated_reposts: 0,
  skipped_hidden: 0,
  error: null,
};

const POLL_INTERVAL = 3;

export default function HomePage() {
  const [scrapeStatus, setScrapeStatus] = useState<ScrapeStatus>(IDLE_STATUS);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(0);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const countdownRef = useRef(0);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setCountdown(0);
  };

  const doPoll = async () => {
    try {
      const res = await fetch(`${API}/api/scrape/status`);
      if (!res.ok) return;
      const data: ScrapeStatus = await res.json();
      setScrapeStatus(data);
      if (data.status !== "running") {
        stopPolling();
        if (data.status === "done") setRefreshKey((k) => k + 1);
      }
    } catch {
      // network blip — keep polling
    }
  };

  const startPolling = () => {
    stopPolling();
    doPoll();
    countdownRef.current = POLL_INTERVAL;
    setCountdown(POLL_INTERVAL);
    pollingRef.current = setInterval(() => {
      countdownRef.current -= 1;
      if (countdownRef.current <= 0) {
        countdownRef.current = POLL_INTERVAL;
        setCountdown(POLL_INTERVAL);
        doPoll();
      } else {
        setCountdown(countdownRef.current);
      }
    }, 1000);
  };

  useEffect(() => () => stopPolling(), []);

  const handleScrape = async (keywords: string, location: string) => {
    setError(null);
    try {
      const res = await fetch(`${API}/api/scrape`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords, location }),
      });
      if (res.status === 409) {
        setError("A scrape is already running.");
        return;
      }
      if (!res.ok) throw new Error(`Scrape failed: ${res.status}`);
      setScrapeStatus({ ...IDLE_STATUS, status: "running" });
      startPolling();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  };

  const handleCancel = async () => {
    await fetch(`${API}/api/scrape/cancel`, { method: "POST" });
  };

  const scrapeMsg =
    scrapeStatus.status === "done"
      ? `Done — ${scrapeStatus.inserted} new, ${scrapeStatus.updated_reposts} reposted`
      : scrapeStatus.status === "error"
      ? `Error: ${scrapeStatus.error}`
      : null;

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-8">
        <div className="h-1 w-16 bg-accent rounded mb-4" />
        <h1 className="text-3xl font-bold text-navy">Aus Job Scraper</h1>
        <p className="text-muted mt-1">Search and scrape recent jobs from Seek.com.au</p>
      </div>

      <div className="p-5 bg-white rounded-xl border border-gray-100 shadow-sm">
        <SearchForm
          onScrape={handleScrape}
          scrapeStatus={scrapeStatus}
          onCancel={handleCancel}
          countdown={countdown}
        />
        {error && <p className="mt-3 text-red-500 text-sm">{error}</p>}
        {scrapeMsg && <p className="mt-3 text-green-600 text-sm">{scrapeMsg}</p>}
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold text-navy mb-4">Saved Jobs</h2>
        <JobList refreshKey={refreshKey} />
      </div>
    </main>
  );
}
