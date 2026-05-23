"use client";
import { useState } from "react";
import { Job } from "@/types";
import JobCard from "./JobCard";

interface Props {
  jobs: Job[];
}

export default function JobList({ jobs }: Props) {
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");

  const filtered = jobs.filter((job) => {
    const kw = keyword.toLowerCase();
    const loc = location.toLowerCase();
    const matchKw =
      !kw ||
      job.title.toLowerCase().includes(kw) ||
      (job.description?.toLowerCase().includes(kw) ?? false);
    const matchLoc =
      !loc ||
      (job.city?.toLowerCase().includes(loc) ?? false) ||
      (job.state?.toLowerCase().includes(loc) ?? false) ||
      (job.suburb?.toLowerCase().includes(loc) ?? false);
    return matchKw && matchLoc;
  });

  return (
    <div>
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
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

      {filtered.length === 0 ? (
        <p className="text-muted text-center py-12">No jobs found.</p>
      ) : (
        <div className="grid gap-4">
          {filtered.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      <p className="text-xs text-muted mt-4 text-right">
        {filtered.length} of {jobs.length} jobs
      </p>
    </div>
  );
}
