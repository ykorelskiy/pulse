import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "https://zyoznyeqvorhztrpgdjw.supabase.co";
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5b3pueWVxdm9yaHp0cnBnZGp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1NzQxNjgsImV4cCI6MjA3MDE1MDE2OH0.z-Z88QGvK7p-94a2E6-w1l3e_z5L-5K6x0J";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

export const getPublicStorageUrl = (path: string): string => {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const { data } = supabase.storage.from("pulse-covers").getPublicUrl(path);
  return data.publicUrl;
};
