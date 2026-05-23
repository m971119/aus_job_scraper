"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Job } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/jobs/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error("Job not found");
        return r.json();
      })
      .then(setJob)
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-10">
        <Link href="/" className="text-primary text-sm hover:underline">
          &larr; Back
        </Link>
        <p className="mt-6 text-red-500">{error}</p>
      </main>
    );
  }

  if (!job) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-10">
        <div className="h-1 w-16 bg-accent rounded mb-6" />
        <div className="text-muted text-sm">Loading...</div>
      </main>
    );
  }

  const location = [job.suburb, job.city, job.state].filter(Boolean).join(", ");

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <Link href="/" className="text-primary text-sm hover:underline">
        &larr; Back to jobs
      </Link>

      <div className="mt-6 bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="h-1 w-12 bg-accent rounded mb-3" />
            <h1 className="text-2xl font-bold text-navy">{job.title}</h1>
            {job.company && (
              <p className="text-primary font-medium mt-1">{job.company}</p>
            )}
          </div>
          {job.is_repost && (
            <span className="shrink-0 text-xs font-semibold px-2 py-1 rounded-full bg-accent/20 text-accent border border-accent/40">
              Reposted
            </span>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted">
          {location && (
            <span>
              <span className="font-medium text-navy">Location</span>{" "}
              {location}
            </span>
          )}
          {job.salary_range && (
            <span>
              <span className="font-medium text-navy">Salary</span>{" "}
              {job.salary_range}
            </span>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-1">
          {job.listed_dates.map((d) => (
            <span
              key={d}
              className="text-xs bg-gray-100 text-muted px-2 py-0.5 rounded"
            >
              {d}
            </span>
          ))}
        </div>

        <div className="mt-5 pt-5 border-t border-gray-100">
          {job.description ? (
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {job.description}
            </p>
          ) : (
            <p className="text-sm text-muted italic">No description available.</p>
          )}
        </div>

        <div className="mt-6">
          <a
            href={job.seek_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-secondary text-white text-sm font-semibold px-4 py-2 rounded-lg hover:opacity-90 transition-opacity"
          >
            View on Seek &rarr;
          </a>
        </div>
      </div>
    </main>
  );
}
