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
      {/* Header */}
      <div className="news-panel-header">
        <div className="news-panel-title-group">
          <Newspaper className="news-icon" size={28} />
          <h2 className="news-panel-title">ГЛАВНЫЕ ПОЗИТИВНЫЕ НОВОСТИ ДНЯ</h2>
        </div>

        <button className="back-to-calendar-btn" onClick={onClose}>
          <ArrowLeft size={18} />
          <span>К календарю</span>
        </button>
      </div>

      <div className="news-panel-date-sub">{formattedTitleDate}</div>

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
