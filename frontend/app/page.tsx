"use client";
import { useState, useCallback, useRef, Suspense } from "react";
import JobList from "@/components/JobList";

export default function HomePage() {
  const [hasFilters, setHasFilters] = useState(false);
  const resetFiltersRef = useRef<() => void>(() => {});

  const handleFilterStateChange = useCallback((has: boolean, reset: () => void) => {
    setHasFilters(has);
    resetFiltersRef.current = reset;
  }, []);

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-8">
        <div className="h-1 w-16 bg-accent rounded mb-4" />
        <h1 className="text-3xl font-bold text-navy">Job Listings</h1>
        <p className="text-muted mt-1">Your saved jobs from Seek.com.au</p>
      </div>

      <div className="flex items-center gap-3 mb-4">
        {hasFilters && (
          <button
            onClick={() => resetFiltersRef.current()}
            className="px-3 py-1 text-xs border border-gray-200 rounded-lg text-muted hover:border-primary hover:text-primary transition-colors"
          >
            Reset filters
          </button>
        )}
      </div>

      <Suspense>
        <JobList refreshKey={0} onFilterStateChange={handleFilterStateChange} />
      </Suspense>
    </main>
  );
}
