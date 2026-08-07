"""RSS feed source adapter using httpx and feedparser."""

import contextlib
import re
import time
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx

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
    """Adapter for RSS/XML news feeds using httpx and feedparser."""

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
        """Fetch latest entries from RSS feed using httpx and feedparser.

        Returns:
            list[NewsArticle]: Parsed news articles.
        """
        articles: list[NewsArticle] = []
        try:
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=True, verify=False
            ) as client:
                headers = {"User-Agent": DEFAULT_USER_AGENT}
                resp = await client.get(self.feed_url, headers=headers)
                if resp.status_code != 200:
                    return []
                raw_xml = resp.text

            parsed = feedparser.parse(raw_xml)
            for entry in parsed.entries:
                headline = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                if not headline or not link:
                    continue

                summary_raw = getattr(entry, "summary", "") or getattr(entry, "description", "")
                summary_clean = strip_html(summary_raw)[:300]

                pub_date = datetime.now(timezone.utc)
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    with contextlib.suppress(Exception):
                        ts = time.mktime(entry.published_parsed)
                        pub_date = datetime.fromtimestamp(ts, tz=timezone.utc)

                articles.append(
                    NewsArticle(
                        source_id=self.source_id,
                        headline=headline,
                        summary=summary_clean,
                        url=link,
                        published_at=pub_date,
                    )
                )
        except Exception:
            pass

        return articles
