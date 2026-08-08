import React, { useState } from "react";
import { ChevronLeft, ChevronRight, Maximize2, FileText, ArrowRight } from "lucide-react";
import { getFormattedHeaderDate, isRedDate } from "../utils/dateUtils";
import { getPublicStorageUrl } from "../lib/supabase";

interface CalendarSheetProps {
  currentDateStr: string;
  issue?: any;
  onPrev: () => void;
  onNext: () => void;
  hasPrev: boolean;
  hasNext: boolean;
  onOpenLightbox: (url: string) => void;
  animating: boolean;
  onToggleNewsView?: () => void;
  isNewsViewOpen?: boolean;
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
  onToggleNewsView,
  isNewsViewOpen,
}) => {
  const header = getFormattedHeaderDate(currentDateStr);
  const [imgError, setImgError] = useState(false);

  React.useEffect(() => {
    setImgError(false);
  }, [currentDateStr, issue?.image_path]);

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

      {/* Main Paper Sheet */}
      <div className={`paper-sheet ${animating ? "tearing-off" : ""}`}>
        {/* Binder Top Header */}
        <div className="binder-header">
          <div className="binder-clip binder-clip-left"></div>
          <div className="binder-clip binder-clip-right"></div>
          <div className="perforation-line"></div>
        </div>

        {/* Date Section */}
        <div className="sheet-date-block">
          <div className={`sheet-day-num ${isRedDate(currentDateStr) ? "red-accent" : ""}`}>
            {header.dayNum}
          </div>
          <div className="sheet-date-text">
            <div className="sheet-month-year">
              {header.monthName.toUpperCase()} {header.year}
            </div>
            <div className={`sheet-weekday ${isRedDate(currentDateStr) ? "red-accent" : ""}`}>
              {header.dayOfWeekName.toUpperCase()}
            </div>
          </div>
          <div className="week-badge">Выпуск {header.dayNum}</div>
        </div>

        {/* Poster / Illustration Section */}
        <div className="cover-frame">
          {coverUrl && !imgError ? (
            <div
              className="cover-wrapper"
              onClick={() => onOpenLightbox(coverUrl)}
              title="Нажмите, чтобы открыть плакат во весь экран"
            >
              <img
                src={coverUrl}
                alt={`Пульс Дня ${header.dayNum} ${header.monthName}`}
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
              <img src="/robot-mascot.jpg" alt="Робот Пульс Дня" className="mascot-placeholder-img" />
              <div className="placeholder-text">
                {currentDateStr.endsWith("08-08") ? "Робот зарисовывает сегодня..." : "В этот день выпуска не было"}
              </div>
            </div>
          )}
        </div>

        {/* Interactive Mascot Pointer Widget */}
        <div className="sheet-footer">
          <div className="mascot-news-widget">
            <img src="/robot-mascot.jpg" alt="Робот Маскот" className="widget-robot-avatar" />
            <div className="widget-speech-bubble">
              <span>События дня в новостях:</span>
            </div>
            <button
              className={`btn-details-toggle ${isNewsViewOpen ? "active" : ""}`}
              onClick={onToggleNewsView}
            >
              <FileText size={18} />
              <span>{isNewsViewOpen ? "К Календарю" : "Подробнее"}</span>
              <ArrowRight className="btn-arrow-icon" size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
