import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Issue, CellState } from "../types";
import {
  getMonthNameNominative,
  formatDateString,
  isRedDate,
  getMskTodayDateString,
} from "../utils/dateUtils";
import { getPublicStorageUrl } from "../lib/supabase";

interface MonthGridProps {
  currentYear: number;
  currentMonth: number; // 0-indexed (0 is Jan)
  issuesMap: Record<string, Issue>;
  selectedDateStr: string;
  onSelectDate: (dateStr: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  canPrevMonth: boolean;
  canNextMonth: boolean;
}

const WEEKDAY_HEADERS = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"];

export const MonthGrid: React.FC<MonthGridProps> = ({
  currentYear,
  currentMonth,
  issuesMap,
  selectedDateStr,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
  canPrevMonth,
  canNextMonth,
}) => {
  const mskToday = getMskTodayDateString();

  // Generate days array for currentYear / currentMonth
  const firstDayOfMonth = new Date(currentYear, currentMonth, 1);
  const lastDayOfMonth = new Date(currentYear, currentMonth + 1, 0);

  // 1 is Monday, 7 is Sunday
  let startDayOfWeek = firstDayOfMonth.getDay();
  if (startDayOfWeek === 0) startDayOfWeek = 7;

  const totalDays = lastDayOfMonth.getDate();

  const cells: Array<{ dateStr: string; dayNum: number; state: CellState; isCurrentMonth: boolean }> = [];

  // Empty leading cells
  for (let i = 1; i < startDayOfWeek; i++) {
    cells.push({ dateStr: "", dayNum: 0, state: "empty_past", isCurrentMonth: false });
  }

  // Days of month
  for (let d = 1; d <= totalDays; d++) {
    const dt = new Date(currentYear, currentMonth, d);
    const dateStr = formatDateString(dt);
    const issue = issuesMap[dateStr];

    let state: CellState = "empty_past";
    if (issue && issue.published) {
      state = "published";
    } else if (dateStr === mskToday && (!issue || !issue.published)) {
      state = "pending_today";
    } else if (dateStr > mskToday) {
      state = "future";
    } else {
      state = "empty_past";
    }

    cells.push({ dateStr, dayNum: d, state, isCurrentMonth: true });
  }

  return (
    <div className="month-grid-container">
      {/* Month Header Navigation */}
      <div className="month-header">
        <button
          className="month-nav-btn"
          onClick={onPrevMonth}
          disabled={!canPrevMonth}
          title="Предыдущий месяц"
        >
          <ChevronLeft size={20} />
        </button>
        <div className="month-title">
          {getMonthNameNominative(currentMonth)} {currentYear}
        </div>
        <button
          className="month-nav-btn"
          onClick={onNextMonth}
          disabled={!canNextMonth}
          title="Следующий месяц"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Weekday Labels Header */}
      <div className="weekday-grid">
        {WEEKDAY_HEADERS.map((w, idx) => (
          <div key={w} className={`weekday-label ${idx >= 5 ? "red-accent" : ""}`}>
            {w}
          </div>
        ))}
      </div>

      {/* Days Grid */}
      <div className="days-grid">
        {cells.map((cell, idx) => {
          if (!cell.isCurrentMonth) {
            return <div key={`empty-${idx}`} className="day-cell cell-empty" />;
          }

          const issue = issuesMap[cell.dateStr];
          const thumbUrl = issue?.thumb128_path ? getPublicStorageUrl(issue.thumb128_path) : "";
          const isSelected = cell.dateStr === selectedDateStr;
          const redDate = isRedDate(cell.dateStr);

          return (
            <div
              key={cell.dateStr}
              className={`day-cell cell-${cell.state} ${isSelected ? "selected" : ""} ${
                redDate ? "red-date" : ""
              }`}
              onClick={() => {
                if (cell.state !== "future") {
                  onSelectDate(cell.dateStr);
                }
              }}
            >
              {/* Red handwritten crayon circle overlay for selected/today */}
              {isSelected && (
                <svg className="handwritten-circle-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
                  <path
                    d="M 15 50 C 12 25, 30 10, 55 12 C 80 14, 92 32, 88 58 C 84 82, 60 92, 35 88 C 15 84, 8 62, 20 45"
                    fill="none"
                    stroke="#dc2626"
                    strokeWidth="4.5"
                    strokeLinecap="round"
                    strokeDasharray="120"
                    className="crayon-stroke-path"
                  />
                </svg>
              )}

              {/* Hand-drawn graphite pencil cross for empty past dates */}
              {cell.state === "empty_past" && (
                <svg className="pencil-cross-svg" viewBox="0 0 40 40">
                  <line x1="8" y1="8" x2="32" y2="32" stroke="#64748b" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
                  <line x1="32" y1="8" x2="8" y2="32" stroke="#64748b" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
                </svg>
              )}

              {cell.state === "published" && thumbUrl ? (
                <div className="cell-thumb-wrapper">
                  <img src={thumbUrl} alt={`Превью ${cell.dayNum}`} className="cell-thumb-img" />
                  <div className={`cell-num-badge ${redDate ? "red-badge" : ""}`}>{cell.dayNum}</div>
                </div>
              ) : (
                <div className="cell-content">
                  <span className={`cell-day-num ${redDate ? "red-num" : ""}`}>{cell.dayNum}</span>
                  {cell.state === "pending_today" && <span className="badge-soon">скоро...</span>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
