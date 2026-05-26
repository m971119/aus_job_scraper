"use client";
import { useState } from "react";
import { ScrapeStatus } from "@/types";
import ScrapeProgress from "./ScrapeProgress";

interface Props {
  onScrape: (keywords: string, location: string) => void;
  scrapeStatus: ScrapeStatus;
  onCancel: () => void;
  countdown: number;
}

export default function SearchForm({ onScrape, scrapeStatus, onCancel, countdown }: Props) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const isRunning = scrapeStatus.status === "running";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (keywords.trim()) onScrape(keywords.trim(), location.trim());
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          placeholder="Keywords (e.g. Python developer)"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          required
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <input
          type="text"
          placeholder="Location (e.g. Melbourne VIC)"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button
          type="submit"
          disabled={isRunning}
          className="px-6 py-2 bg-secondary text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {isRunning ? "Scraping..." : "Scrape Seek"}
        </button>
      </form>

      <ScrapeProgress
        status={scrapeStatus.status}
        phase={scrapeStatus.phase}
        currentPage={scrapeStatus.current_page}
        jobsScraped={scrapeStatus.jobs_scraped}
        jobsCompared={scrapeStatus.jobs_compared}
        onCancel={onCancel}
        countdown={countdown}
      />
    </>
  );
}
