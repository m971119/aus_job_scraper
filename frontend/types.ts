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
  tags: Tag[];
}

export interface JobsPage {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}
