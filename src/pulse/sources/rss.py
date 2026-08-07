"""RSS feed source adapter."""

from pulse.sources.base import BaseSourceAdapter, NewsArticle


class RSSSourceAdapter(BaseSourceAdapter):
    """Adapter for RSS/XML news feeds using feedparser."""

    def __init__(self, source_id: str, feed_url: str) -> None:
        self.source_id = source_id
        self.feed_url = feed_url

    async def fetch_latest(self) -> list[NewsArticle]:
        """Fetch latest entries from RSS feed.

        Returns:
            list[NewsArticle]: Parsed news articles.
        """
        raise NotImplementedError
