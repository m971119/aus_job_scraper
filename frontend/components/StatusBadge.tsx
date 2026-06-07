import { JobStatus } from "@/types";

export const JOB_STATUSES: JobStatus[] = [
  "SAVED",
  "APPLIED",
  "INTERVIEWING",
  "OFFER",
  "ACCEPTED",
  "REJECTED",
  "WITHDRAWN",
  "GHOSTED",
];

export const STATUS_LABELS: Record<JobStatus, string> = {
  SAVED: "Saved",
  APPLIED: "Applied",
  INTERVIEWING: "Interviewing",
  OFFER: "Offer",
  ACCEPTED: "Accepted",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
  GHOSTED: "Ghosted",
};

const STATUS_STYLES: Record<JobStatus, string> = {
  SAVED: "bg-gray-100 text-gray-500 border-gray-300",
  APPLIED: "bg-primary/10 text-primary border-primary/30",
  INTERVIEWING: "bg-accent/20 text-amber-700 border-accent/40",
  OFFER: "bg-green-100 text-green-700 border-green-300",
  ACCEPTED: "bg-green-200 text-green-800 border-green-400",
  REJECTED: "bg-red-100 text-red-600 border-red-300",
  WITHDRAWN: "bg-slate-100 text-slate-500 border-slate-300",
  GHOSTED: "bg-secondary/10 text-secondary border-secondary/30",
};

export default function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`text-xs font-semibold px-2 py-1 rounded-full border ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
