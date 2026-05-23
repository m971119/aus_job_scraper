import { Job } from "@/types";

interface Props {
  job: Job;
}

export default function JobCard({ job }: Props) {
  const location = [job.suburb, job.city, job.state].filter(Boolean).join(", ");

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <a
            href={job.seek_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary font-semibold text-lg hover:underline truncate block"
          >
            {job.title}
          </a>
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

      <div className="mt-3 flex flex-wrap gap-1">
        {job.listed_dates.map((d) => (
          <span key={d} className="text-xs bg-gray-100 text-muted px-2 py-0.5 rounded">
            {d}
          </span>
        ))}
      </div>
    </div>
  );
}
