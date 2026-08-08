import React, { useState } from "react";
import { ChevronLeft, ChevronRight, Maximize2 } from "lucide-react";
import type { Issue } from "../types";
import { getFormattedHeaderDate } from "../utils/dateUtils";
import { getPublicStorageUrl } from "../lib/supabase";

interface CalendarSheetProps {
  currentDateStr: string;
  issue?: Issue;
  onPrev: () => void;
  onNext: () => void;
  hasPrev: boolean;
  hasNext: boolean;
  onOpenLightbox: (url: string) => void;
  animating: boolean;
}

export const CalendarSheet: React.FC<CalendarSheetProps> = ({
  currentDateStr,
  issue,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  onOpenLightbox,
  animating,
}) => {
  const header = getFormattedHeaderDate(currentDateStr);
  const [imgError, setImgError] = useState(false);

  const coverUrl = issue?.image_path ? getPublicStorageUrl(issue.image_path) : "";

  return (
    <div className="sheet-container">
      {/* Side Navigation Arrows */}
      <button
        className={`nav-arrow nav-arrow-left ${!hasPrev ? "disabled" : ""}`}
        onClick={onPrev}
        disabled={!hasPrev}
        title="Предыдущий день с выпуском (←)"
      >
        <ChevronLeft size={32} />
      </button>

      <button
        className={`nav-arrow nav-arrow-right ${!hasNext ? "disabled" : ""}`}
        onClick={onNext}
        disabled={!hasNext}
        title="Следующий день с выпуском (→)"
      >
        <ChevronRight size={32} />
      </button>

      {/* Main Parchment Tear-off Sheet */}
      <div className={`paper-sheet ${animating ? "tearing-off" : ""}`}>
        {/* Metal Binder Clips Header */}
        <div className="binder-header">
          <div className="binder-clip binder-clip-left"></div>
          <div className="binder-clip binder-clip-right"></div>
          <div className="perforation-line"></div>
        </div>

        {/* Calendar Sheet Date Banner */}
        <div className="sheet-date-block">
          <div className={`sheet-day-num ${header.isRed ? "red-accent" : ""}`}>{header.dayNum}</div>
          <div className="sheet-date-text">
            <div className={`sheet-month-year ${header.isRed ? "red-accent" : ""}`}>
              {header.monthName} {header.year}
            </div>
            <div className={`sheet-weekday ${header.isRed ? "red-accent" : ""}`}>
              {header.dayOfWeekName}
            </div>
          </div>
          <div className="week-badge">НЕДЕЛЯ {header.weekNum}</div>
        </div>

        {/* Daily Cover Illustration Frame */}
        <div className="cover-frame">
          {issue && coverUrl && !imgError ? (
            <div className="cover-wrapper" onClick={() => onOpenLightbox(coverUrl)}>
              <img
                src={coverUrl}
                alt={issue.title || `Пульс дня — ${currentDateStr}`}
                className="cover-image"
                onError={() => setImgError(true)}
              />
              <div className="cover-hover-overlay">
                <Maximize2 size={24} color="#fff" />
                <span>Открыть плакат</span>
              </div>
            </div>
          ) : (
            <div className="cover-placeholder">
              <div className="placeholder-logo">ПУЛЬС ДНЯ</div>
              <div className="placeholder-text">
                {currentDateStr.endsWith("08-08") ? "Выпуск загружается..." : "В этот день выпуска не было"}
              </div>
            </div>
          )}
        </div>

        {/* Footer info or News placeholder */}
        <div className="sheet-footer">
          <div className="sheet-brand-label">ПУЛЬС ДНЯ — ЕЖЕДНЕВНЫЙ ОТРИВНОЙ КАЛЕНДАРЬ</div>
        </div>
      </div>
    </div>
  );
};
