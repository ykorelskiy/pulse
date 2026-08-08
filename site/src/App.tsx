import { useState, useEffect, useCallback } from "react";
import { supabase } from "./lib/supabase";
import type { Issue } from "./types";
import { CalendarSheet } from "./components/CalendarSheet";
import { MonthGrid } from "./components/MonthGrid";
import { Lightbox } from "./components/Lightbox";
import {
  parseDateString,
  formatDateString,
} from "./utils/dateUtils";

export function App() {
  // Parse date from URL path /YYYY/MM/DD or default to latest published / today
  const parseUrlDate = (): string => {
    const path = window.location.pathname;
    const match = path.match(/^\/(\d{4})\/(\d{2})\/(\d{2})$/);
    if (match) {
      return `${match[1]}-${match[2]}-${match[3]}`;
    }
    return "2026-08-08"; // Default to today issue
  };

  const [selectedDateStr, setSelectedDateStr] = useState<string>(parseUrlDate());
  const [issuesMap, setIssuesMap] = useState<Record<string, Issue>>({});
  const [publishedDates, setPublishedDates] = useState<string[]>([]);
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  const [animating, setAnimating] = useState(false);
  const [showMobileCalendar, setShowMobileCalendar] = useState(false);

  const currentDate = parseDateString(selectedDateStr);
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth();

  // Fetch published issues from Supabase
  const fetchIssues = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from("site_issues")
        .select("*")
        .eq("published", true)
        .order("issue_date", { ascending: false });

      if (!error && data) {
        const map: Record<string, Issue> = {};
        const dates: string[] = [];
        data.forEach((item: Issue) => {
          map[item.issue_date] = item;
          dates.push(item.issue_date);
        });
        setIssuesMap(map);
        setPublishedDates(dates.sort());
      }
    } catch (err) {
      console.error("Failed to fetch site issues:", err);
    }
  }, []);

  useEffect(() => {
    fetchIssues();
  }, [fetchIssues]);

  // Update URL history when date changes
  const navigateToDate = (dateStr: string) => {
    if (dateStr === selectedDateStr) return;
    setAnimating(true);
    setTimeout(() => {
      setSelectedDateStr(dateStr);
      const [y, m, d] = dateStr.split("-");
      window.history.pushState({}, "", `/${y}/${m}/${d}`);
      setAnimating(false);
    }, 250);
  };

  // Listen to popstate (browser back/forward)
  useEffect(() => {
    const handlePopState = () => {
      setSelectedDateStr(parseUrlDate());
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // Find previous & next published issue date
  const prevPublishedDate = [...publishedDates]
    .reverse()
    .find((d) => d < selectedDateStr);
  const nextPublishedDate = publishedDates.find((d) => d > selectedDateStr);

  const handlePrev = () => {
    if (prevPublishedDate) navigateToDate(prevPublishedDate);
  };

  const handleNext = () => {
    if (nextPublishedDate) navigateToDate(nextPublishedDate);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (lightboxUrl) return; // Don't trigger if lightbox is open
      if (e.key === "ArrowLeft" && prevPublishedDate) handlePrev();
      if (e.key === "ArrowRight" && nextPublishedDate) handleNext();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [prevPublishedDate, nextPublishedDate, lightboxUrl]);

  // Month navigation
  const handlePrevMonth = () => {
    const prevMonthDate = new Date(currentYear, currentMonth - 1, 1);
    navigateToDate(formatDateString(prevMonthDate));
  };

  const handleNextMonth = () => {
    const nextMonthDate = new Date(currentYear, currentMonth + 1, 1);
    navigateToDate(formatDateString(nextMonthDate));
  };

  const currentIssue = issuesMap[selectedDateStr];

  return (
    <div className="app-root">
      {/* Navbar Header */}
      <header className="top-navbar">
        <div className="brand-title">
          <span>ПУЛЬС ДНЯ</span>
          <span className="brand-badge">2026</span>
        </div>
        <div className="meta-right" style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <button
            className="month-nav-btn"
            style={{ width: "auto", padding: "0 12px", fontSize: "13px" }}
            onClick={() => setShowMobileCalendar(!showMobileCalendar)}
          >
            📅 {showMobileCalendar ? "Скрыть календарь" : "Календарь архива"}
          </button>
        </div>
      </header>

      {/* Main Grid Content */}
      <main className="main-container">
        {/* Left Column: Tear-off Sheet */}
        <section className="left-section">
          <CalendarSheet
            currentDateStr={selectedDateStr}
            issue={currentIssue}
            onPrev={handlePrev}
            onNext={handleNext}
            hasPrev={!!prevPublishedDate}
            hasNext={!!nextPublishedDate}
            onOpenLightbox={(url) => setLightboxUrl(url)}
            animating={animating}
          />
        </section>

        {/* Right Column: Month Calendar Grid */}
        <section className={`right-section ${showMobileCalendar ? "show-mobile" : ""}`}>
          <MonthGrid
            currentYear={currentYear}
            currentMonth={currentMonth}
            issuesMap={issuesMap}
            selectedDateStr={selectedDateStr}
            onSelectDate={(d) => navigateToDate(d)}
            onPrevMonth={handlePrevMonth}
            onNextMonth={handleNextMonth}
            canPrevMonth={currentMonth > 6 || currentYear > 2026}
            canNextMonth={currentMonth < 11 || currentYear < 2026}
          />
        </section>
      </main>

      {/* Lightbox Modal */}
      {lightboxUrl && (
        <Lightbox
          imageUrl={lightboxUrl}
          title={currentIssue?.title || `Пульс дня — ${selectedDateStr}`}
          onClose={() => setLightboxUrl(null)}
        />
      )}
    </div>
  );
}

export default App;
