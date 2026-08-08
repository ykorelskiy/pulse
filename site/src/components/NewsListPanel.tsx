import React from "react";
import { ArrowLeft, ExternalLink, Newspaper } from "lucide-react";
import { getFormattedHeaderDate } from "../utils/dateUtils";

interface NewsItem {
  text: string;
  url?: string;
  source?: string;
}

interface NewsListPanelProps {
  currentDateStr: string;
  newsItems: NewsItem[];
  title?: string;
  onClose: () => void;
}

export const NewsListPanel: React.FC<NewsListPanelProps> = ({
  currentDateStr,
  newsItems,
  onClose,
}) => {
  const headerDate = getFormattedHeaderDate(currentDateStr);
  const formattedTitleDate = `${headerDate.dayNum} ${headerDate.monthName.toUpperCase()} ${headerDate.year}`;

  const top15 = (newsItems || []).slice(0, 15);

  return (
    <div className="news-panel-container fade-in-panel">
      {/* 2-line Strict Aligned Header Box */}
      <div className="news-panel-header-box">
        <div className="news-title-left">
          <Newspaper className="news-icon" size={32} />
          <div className="news-title-lines">
            <div className="title-row-1">ГЛАВНЫЕ ПОЗИТИВНЫЕ</div>
            <div className="title-row-2">НОВОСТИ ДНЯ</div>
          </div>
        </div>

        <div className="news-controls-right">
          <div className="control-row-1">
            <button
              className="back-arrow-pill-btn"
              onClick={onClose}
              title="Вернуться к календарю месяца"
            >
              <ArrowLeft size={18} />
            </button>
          </div>
          <div className="control-row-2">
            <div className="news-date-sub">{formattedTitleDate}</div>
          </div>
        </div>
      </div>

      {/* Clean 1-Column News List with Right-Aligned Equal-Width Buttons */}
      {top15.length > 0 ? (
        <div className="news-items-clean-list">
          {top15.map((item, idx) => (
            <div key={idx} className="news-clean-item">
              <div className="news-content-left">
                <span className="news-num-prefix">{idx + 1}.</span>
                <span className="news-clean-text">{item.text}</span>
              </div>

              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="news-source-fixed-btn"
                >
                  <span>{item.source || "Источник"}</span>
                  <ExternalLink size={12} />
                </a>
              ) : (
                <div className="news-source-fixed-placeholder" />
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="news-empty-state">
          <img
            src="/robot-mascot.jpg"
            alt="Робот Пульс Дня"
            className="news-empty-robot"
          />
          <p className="news-empty-text">
            Робот ещё собирает и систематизирует новости за этот день...
          </p>
        </div>
      )}
    </div>
  );
};
