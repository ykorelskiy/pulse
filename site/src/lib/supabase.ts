import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "https://zyoznyeqvorhztrpgdjw.supabase.co";
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5b3pueWVxdm9yaHp0cnBnZGp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxMTAxNjgsImV4cCI6MjEwMTY4NjE2OH0.-Bvwocejd5LpsCg7sPTVO9rBt6i2hxM4UePkIpRNsnI";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

export const getPublicStorageUrl = (path: string): string => {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const { data } = supabase.storage.from("pulse-covers").getPublicUrl(path);
  return data.publicUrl;
};
