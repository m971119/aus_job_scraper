"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Job } from "@/types";
import TagManager from "@/components/TagManager";
import NotesEditor from "@/components/NotesEditor";
import SponsorLookup from "@/components/SponsorLookup";
import StatusBadge, { JOB_STATUSES, STATUS_LABELS } from "@/components/StatusBadge";
import { JobStatus } from "@/types";

function BackButton() {
  return (
    <Link
      href="/"
      className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary border border-primary px-3 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-colors"
    >
      &larr; Back to jobs
    </Link>
  );
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [sponsors, setSponsors] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);

  const handleHide = async () => {
    await fetch(`${API}/api/jobs/${id}/hide`, { method: "PATCH" });
    router.push("/");
  };

  const handleUnhide = async () => {
    await fetch(`${API}/api/jobs/${id}/unhide`, { method: "PATCH" });
    router.push("/");
  };

  const handleStatusChange = async (newStatus: JobStatus) => {
    setStatus(newStatus);
    await fetch(`${API}/api/jobs/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
  };

  useEffect(() => {
    fetch(`${API}/api/sponsors`).then((r) => r.json()).then((d) => setSponsors(d.sponsors));
  }, []);

  useEffect(() => {
    fetch(`${API}/api/jobs/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error("Job not found");
        return r.json();
      })
      .then((d) => { setJob(d); setStatus(d.status); })
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-10">
        <BackButton />
        <p className="mt-6 text-red-500">{error}</p>
      </main>
    );
  }

  if (!job) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-10">
        <BackButton />
        <div className="mt-6 text-muted text-sm">Loading...</div>
      </main>
    );
  }

  const location = [job.suburb, job.city, job.state].filter(Boolean).join(", ");

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <BackButton />

      <div className="mt-6 bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="h-1 w-12 bg-accent rounded mb-3" />
            <h1 className="text-2xl font-bold text-navy">
              <a
                href={job.seek_url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary transition-colors"
              >
                {job.title}
              </a>
            </h1>
            {job.company && (
              <div className="flex items-center gap-2 mt-1">
                <p className="text-primary font-medium">{job.company}</p>
                <SponsorLookup companyName={job.company} sponsors={sponsors} />
              </div>
            )}
            <div className="mt-2 flex items-center gap-2">
              <span className="text-xs text-muted font-medium">Status</span>
              <select
                value={status ?? "SAVED"}
                onChange={(e) => handleStatusChange(e.target.value as JobStatus)}
                className="text-xs border border-gray-200 rounded-lg px-2 py-1 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {JOB_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </option>
                ))}
              </select>
            </div>
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

        <TagManager jobId={job.id} initialTags={job.tags ?? []} />

        <NotesEditor jobId={job.id} initialNotes={job.notes ?? null} />

        <div className="mt-6 flex items-center gap-3">
          <a
            href={job.seek_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-secondary text-white text-sm font-semibold px-4 py-2 rounded-lg hover:opacity-90 transition-opacity"
          >
            View on Seek &rarr;
          </a>
          {job.is_hidden ? (
            <button
              onClick={handleUnhide}
              className="text-sm text-muted hover:text-green-600 transition-colors px-3 py-2 rounded-lg hover:bg-green-50"
            >
              Unhide
            </button>
          ) : (
            <button
              onClick={handleHide}
              className="text-sm text-muted hover:text-red-500 transition-colors px-3 py-2 rounded-lg hover:bg-red-50"
            >
              Not interested
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
