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

  return (
    <div className="news-panel-container">
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

      {/* News Items List */}
      {newsItems && newsItems.length > 0 ? (
        <div className="news-items-list">
          {newsItems.slice(0, 10).map((item, idx) => (
            <div key={idx} className="news-item-card">
              <div className="news-item-num">{idx + 1}</div>

              <div className="news-item-body">
                <p className="news-item-text">{item.text}</p>

                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="news-source-link"
                  >
                    <span>{item.source || "Первоисточник"}</span>
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>
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
