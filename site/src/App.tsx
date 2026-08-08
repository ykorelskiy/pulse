import React, { useState, useEffect } from "react";
import { supabase } from "./lib/supabase";
import type { Issue } from "./types";
import { CalendarSheet } from "./components/CalendarSheet";
import { MonthGrid } from "./components/MonthGrid";
import { NewsListPanel } from "./components/NewsListPanel";
import { Lightbox } from "./components/Lightbox";
import { formatDateString, parseDateString } from "./utils/dateUtils";

export const App: React.FC = () => {
  const [issuesMap, setIssuesMap] = useState<Record<string, Issue>>({});
  const [publishedDates, setPublishedDates] = useState<string[]>([]);
  const [selectedDateStr, setSelectedDateStr] = useState<string>("2026-08-08");
  const [currentYear, setCurrentYear] = useState<number>(2026);
  const [currentMonth, setCurrentMonth] = useState<number>(7);
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  const [animating, setAnimating] = useState<boolean>(false);
  const [rightPanelView, setRightPanelView] = useState<"calendar" | "news">("calendar");

  useEffect(() => {
    const path = window.location.pathname;
    const match = path.match(/^\/(\d{4})\/(\d{2})\/(\d{2})$/);
    if (match) {
      const targetDate = `${match[1]}-${match[2]}-${match[3]}`;
      setSelectedDateStr(targetDate);
      setCurrentYear(parseInt(match[1], 10));
      setCurrentMonth(parseInt(match[2], 10) - 1);
    }
  }, []);

  useEffect(() => {
    const loadIssues = async () => {
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

          dates.sort();
          setIssuesMap(map);
          setPublishedDates(dates);

          if (dates.length > 0 && !window.location.pathname.match(/^\/\d{4}\/\d{2}\/\d{2}$/)) {
            const latestDate = dates[dates.length - 1];
            setSelectedDateStr(latestDate);
            const dt = parseDateString(latestDate);
            setCurrentYear(dt.getFullYear());
            setCurrentMonth(dt.getMonth());
          }
        }
      } catch (err) {
        console.error("Error fetching published issues:", err);
      }
    };

    loadIssues();
  }, []);

  const navigateToDate = (dateStr: string) => {
    if (dateStr === selectedDateStr) return;
    setAnimating(true);
    setTimeout(() => {
      setSelectedDateStr(dateStr);
      const dt = parseDateString(dateStr);
      setCurrentYear(dt.getFullYear());
      setCurrentMonth(dt.getMonth());

      const [y, m, d] = dateStr.split("-");
      window.history.pushState({}, "", `/${y}/${m}/${d}`);
      setAnimating(false);
    }, 250);
  };

  const currentIndex = publishedDates.indexOf(selectedDateStr);
  const prevPublishedDate = currentIndex > 0 ? publishedDates[currentIndex - 1] : null;
  const nextPublishedDate =
    currentIndex >= 0 && currentIndex < publishedDates.length - 1
      ? publishedDates[currentIndex + 1]
      : null;

  const handlePrev = () => {
    if (prevPublishedDate) navigateToDate(prevPublishedDate);
  };

  const handleNext = () => {
    if (nextPublishedDate) navigateToDate(nextPublishedDate);
  };

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
      {/* Main Grid Content (Unified Natural Scroll) */}
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
            onToggleNewsView={() =>
              setRightPanelView(rightPanelView === "calendar" ? "news" : "calendar")
            }
            isNewsViewOpen={rightPanelView === "news"}
          />
        </section>

        {/* Right Column: Month Calendar Grid OR News List Panel */}
        <section className="right-section">
          {rightPanelView === "news" ? (
            <NewsListPanel
              currentDateStr={selectedDateStr}
              newsItems={currentIssue?.news || []}
              title={currentIssue?.title}
              onClose={() => setRightPanelView("calendar")}
            />
          ) : (
            <MonthGrid
              currentYear={currentYear}
              currentMonth={currentMonth}
              issuesMap={issuesMap}
              selectedDateStr={selectedDateStr}
              onSelectDate={(d) => navigateToDate(d)}
              onPrevMonth={handlePrevMonth}
              onNextMonth={handleNextMonth}
              canPrevMonth={currentYear > 2026 || (currentYear === 2026 && currentMonth > 6)}
              canNextMonth={true}
            />
          )}
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
};

export default App;
