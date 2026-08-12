import React from "react";
import { ArrowLeft, Newspaper } from "lucide-react";
import { getFormattedHeaderDate } from "../utils/dateUtils";
import type { NewsItem } from "../types";

interface NewsListPanelProps {
  currentDateStr: string;
  newsItems: NewsItem[];
  title?: string;
  onClose: () => void;
  isClosing?: boolean;
}

function getShortSourceLabel(rawSource?: string, rawSourceName?: string): string {
  const raw = (rawSource || rawSourceName || "Источник").trim();
  const cleaned = raw.split(/\s*[\u2014\u2013-]\s*/)[0].trim();
  if (cleaned === "Календарь праздников") return "Calend.ru";
  return cleaned || "Источник";
}

export const NewsListPanel: React.FC<NewsListPanelProps> = ({
  currentDateStr,
  newsItems,
  onClose,
  isClosing,
}) => {
  const headerDate = getFormattedHeaderDate(currentDateStr);
  const formattedTitleDate = `${headerDate.dayNum} ${headerDate.monthName.toUpperCase()} ${headerDate.year}`;

  const top15 = (newsItems || []).slice(0, 15);

  return (
    <div className={`news-panel-container ${isClosing ? "closing-exit" : "fade-in-panel"}`}>
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

      {/* Clean 1-Column News List (Entire Row Clickable) */}
      {top15.length > 0 ? (
        <div className="news-items-clean-list">
          {top15.map((item, idx) => {
            const newsText = (
              item.text ||
              item.headline ||
              item.ru_headline ||
              item.summary ||
              ""
            ).trim();
            const targetUrl = item.url || item.source_url;
            const hasUrl = !!targetUrl;
            const sourceLabel = getShortSourceLabel(item.source, item.source_name);
            const RowWrapper = hasUrl ? "a" : "div";
            const rowProps = hasUrl
              ? {
                  href: targetUrl,
                  target: "_blank",
                  rel: "noopener noreferrer",
                  className: "news-clean-item clickable-news-row",
                }
              : {
                  className: "news-clean-item",
                };

            return (
              <RowWrapper key={idx} {...(rowProps as any)}>
                <div className="news-content-left">
                  <span className="news-num-prefix">{idx + 1}.</span>
                  <span className="news-clean-text">{newsText}</span>
                </div>

                {hasUrl ? (
                  <span className="news-source-fixed-btn">
                    <span className="news-source-text">{sourceLabel}</span>
                  </span>
                ) : (
                  <div className="news-source-fixed-placeholder" />
                )}
              </RowWrapper>
            );
          })}
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
