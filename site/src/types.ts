export interface NewsItem {
  tag?: string;
  text?: string;
  headline?: string;
  ru_headline?: string;
  summary?: string;
  url?: string;
  source_url?: string;
  source?: string;
  source_name?: string;
}

export interface Issue {
  id: string;
  issue_date: string; // YYYY-MM-DD
  image_path: string;
  thumb480_path: string;
  thumb128_path: string;
  title?: string;
  news?: NewsItem[];
  published: boolean;
  published_at?: string;
  created_at?: string;
}

export type CellState = "published" | "empty_past" | "pending_today" | "future";

