"use client";
import { useState } from "react";
import Link from "next/link";
import { Job, Tag } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  job: Job;
  allTags: Tag[];
  sponsors: string[];
  onHide?: (id: number) => void;
}

export default function JobCard({ job, allTags, sponsors, onHide }: Props) {
  const [tags, setTags] = useState<Tag[]>(job.tags ?? []);
  const [panelOpen, setPanelOpen] = useState(false);

  const addTag = async (tag: Tag) => {
    await fetch(`${API}/api/jobs/${job.id}/tags/${tag.id}`, { method: "POST" });
    setTags((prev) => [...prev, tag]);
    setPanelOpen(false);
  };

  const removeTag = async (tag: Tag) => {
    await fetch(`${API}/api/jobs/${job.id}/tags/${tag.id}`, { method: "DELETE" });
    setTags((prev) => prev.filter((t) => t.id !== tag.id));
  };

  const appliedIds = new Set(tags.map((t) => t.id));
  const location = [job.suburb, job.city, job.state].filter(Boolean).join(", ");

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <Link
            href={`/jobs/${job.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary font-semibold text-lg hover:underline truncate block"
          >
            {job.title}
          </Link>
          {job.company && (
            <p className="text-navy font-medium mt-0.5">{job.company}</p>
          )}
        </div>
        {job.is_repost && (
          <span className="shrink-0 text-xs font-semibold px-2 py-1 rounded-full bg-accent/20 text-accent border border-accent/40">
            Reposted
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
        {location && <span>{location}</span>}
        {job.salary_range && <span>{job.salary_range}</span>}
      </div>

      {job.description && (
        <p className="mt-3 text-sm text-gray-600 line-clamp-3">{job.description}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {tags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20"
          >
            {tag.name}
            <button
              onClick={() => removeTag(tag)}
              className="ml-0.5 hover:text-red-500 transition-colors leading-none"
              aria-label={`Remove ${tag.name}`}
            >
              &times;
            </button>
          </span>
        ))}
        <button
          onClick={() => setPanelOpen((o) => !o)}
          aria-label="Add tag"
          className={`w-5 h-5 rounded-full border text-sm flex items-center justify-center transition-colors ${
            panelOpen
              ? "border-primary bg-primary/10 text-primary"
              : "border-gray-300 text-muted hover:border-primary hover:text-primary"
          }`}
        >
          +
        </button>
      </div>

      {panelOpen && (
        <div className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
            All tags — click to add or remove
          </p>
          <div className="flex flex-wrap gap-1.5">
            {allTags.map((tag) =>
              appliedIds.has(tag.id) ? (
                <button
                  key={tag.id}
                  onClick={() => removeTag(tag)}
                  className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20 hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-colors"
                >
                  {tag.name} &times;
                </button>
              ) : (
                <button
                  key={tag.id}
                  onClick={() => addTag(tag)}
                  className="text-xs px-2.5 py-1 rounded-full bg-white text-gray-500 border border-gray-200 hover:border-primary hover:text-primary transition-colors"
                >
                  {tag.name}
                </button>
              )
            )}
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-1">
        {job.listed_dates.map((d) => (
          <span key={d} className="text-xs bg-gray-100 text-muted px-2 py-0.5 rounded">
            {d}
          </span>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
        <Link
          href={`/jobs/${job.id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-sm font-semibold text-primary border border-primary px-3 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-colors"
        >
          View details
        </Link>
        {onHide && (
          <button
            onClick={() => onHide(job.id)}
            className="text-xs text-muted hover:text-red-500 transition-colors px-2 py-1 rounded hover:bg-red-50"
          >
            Not interested
          </button>
        )}
      </div>
    </div>
  );
}
