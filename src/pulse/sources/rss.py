"""RSS feed source adapter using feedparser."""

import re
import time
from datetime import datetime, timezone
from typing import Any

import feedparser

from pulse.sources.base import BaseSourceAdapter, NewsArticle

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def strip_html(text: Any) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not text or not isinstance(text, str):
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    return " ".join(clean.split()).strip()



class RSSSourceAdapter(BaseSourceAdapter):
    """Adapter for RSS/XML news feeds using feedparser."""

    def __init__(
        self,
        source_id: str,
        feed_url: str,
        name: str = "",
        category: str = "general",
    ) -> None:
        self.source_id = source_id
        self.feed_url = feed_url
        self.url = feed_url
        self.name = name or source_id
        self.category = category

    async def fetch_latest(self) -> list[NewsArticle]:
        """Fetch latest entries from RSS feed.

        Returns:
            list[NewsArticle]: Parsed news articles.
        """
        parsed = feedparser.parse(self.feed_url, agent=DEFAULT_USER_AGENT)
        articles: list[NewsArticle] = []

        for entry in parsed.entries:
            headline = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not headline or not link:
                continue

            summary_raw = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary_clean = strip_html(summary_raw)[:300]

            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
                published_at = dt
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
                published_at = dt

            articles.append(
                NewsArticle(
                    source_id=self.source_id,
                    headline=headline,
                    url=link,
                    summary=summary_clean,
                    published_at=published_at,
                )
            )

        return articles
