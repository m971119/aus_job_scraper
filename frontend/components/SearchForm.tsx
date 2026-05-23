"use client";
import { useState } from "react";

interface Props {
  onScrape: (keywords: string, location: string) => void;
  loading: boolean;
}

export default function SearchForm({ onScrape, loading }: Props) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (keywords.trim()) onScrape(keywords.trim(), location.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
      <input
        type="text"
        placeholder="Keywords (e.g. Python developer)"
        value={keywords}
        onChange={(e) => setKeywords(e.target.value)}
        required
        className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#209dd7]"
      />
      <input
        type="text"
        placeholder="Location (e.g. Melbourne VIC)"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#209dd7]"
      />
      <button
        type="submit"
        disabled={loading}
        className="px-6 py-2 bg-[#753991] text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
      >
        {loading ? "Scraping..." : "Scrape Seek"}
      </button>
    </form>
  );
}
