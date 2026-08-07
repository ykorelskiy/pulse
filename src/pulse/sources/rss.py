"""RSS feed source adapter using feedparser."""

import time
from datetime import datetime, timezone

import feedparser

from pulse.sources.base import BaseSourceAdapter, NewsArticle


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
        parsed = feedparser.parse(self.feed_url)
        articles: list[NewsArticle] = []

        for entry in parsed.entries:
            headline = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not headline or not link:
                continue

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
                    published_at=published_at,
                )
            )

        return articles
