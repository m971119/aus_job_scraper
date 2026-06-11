export type JobStatus =
  | "SAVED"
  | "APPLIED"
  | "INTERVIEWING"
  | "OFFER"
  | "ACCEPTED"
  | "REJECTED"
  | "WITHDRAWN"
  | "GHOSTED";

export interface Tag {
  id: number;
  name: string;
}

export interface Job {
  id: number;
  seek_url: string;
  title: string;
  company: string | null;
  description: string | null;
  state: string | null;
  city: string | null;
  suburb: string | null;
  salary_range: string | null;
  listed_dates: string[];
  latest_listing_date: string | null;
  is_repost: boolean;
  is_hidden: boolean;
  status: JobStatus;
  notes: string | null;
  tags: Tag[];
  resume_version_id: number | null;
}

export interface JobsPage {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface ScrapeStatus {
  status: string;
  phase: string;
  current_page: number;
  jobs_scraped: number;
  jobs_compared: number;
  inserted: number;
  updated_reposts: number;
  skipped_hidden: number;
  error: string | null;
}

export interface ModelInfo {
  id: string;
  label: string;
}

export interface MessageOut {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface CoverLetterOut {
  id: number;
  job_id: number;
  resume_version_id: number;
  content: string;
  conversation_id: number;
  messages: MessageOut[];
  updated_at: string;
}

export interface AdvisorOut {
  conversation_id: number;
  messages: MessageOut[];
}

export interface ResumeVersionMeta {
  id: number;
  label: string;
  created_at: string;
}
