import Link from "next/link";
import { Job } from "@/types";

interface Props {
  job: Job;
  onHide?: (id: number) => void;
}

export default function JobCard({ job, onHide }: Props) {
  const location = [job.suburb, job.city, job.state].filter(Boolean).join(", ");

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <Link
            href={`/jobs/${job.id}`}
            className="text-primary font-semibold text-lg hover:underline truncate block"
          >
            {job.title}
          </Link>
          {job.company && (
            <p className="text-navy font-medium mt-0.5">{job.company}</p>
          )}
        </div>
        <div className="flex shrink-0 gap-1.5">
          {job.is_repost && (
            <span className="text-xs font-semibold px-2 py-1 rounded-full bg-accent/20 text-accent border border-accent/40">
              Reposted
            </span>
          )}
          {job.tags?.some((t) => t.name.toLowerCase() === "interested") && (
            <span className="text-xs font-semibold px-2 py-1 rounded-full bg-primary/15 text-primary border border-primary/30">
              Interested
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
        {location && <span>{location}</span>}
        {job.salary_range && <span>{job.salary_range}</span>}
      </div>

      {job.description && (
        <p className="mt-3 text-sm text-gray-600 line-clamp-3">{job.description}</p>
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
