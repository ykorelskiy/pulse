export interface Issue {
  id: string;
  issue_date: string; // YYYY-MM-DD
  image_path: string;
  thumb480_path: string;
  thumb128_path: string;
  title?: string;
  news?: Array<{ tag?: string; text: string; source_url?: string }>;
  published: boolean;
  published_at?: string;
  created_at?: string;
}

export type CellState = "published" | "empty_past" | "pending_today" | "future";
