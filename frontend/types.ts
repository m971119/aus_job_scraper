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
  is_repost: boolean;
}
