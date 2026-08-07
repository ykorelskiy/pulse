"""Topic ranker module."""

from pulse.sources.base import NewsArticle


class TopicRanker:
    """Ranks news clusters by daily relevance and editorial criteria."""

    def select_top_news(self, clusters: list[list[NewsArticle]], limit: int = 5) -> list[str]:
        """Select top N news story summaries for daily brief.

        Args:
            clusters: Grouped article clusters.
            limit: Maximum number of headlines to select.

        Returns:
            list[str]: Ranked headline summaries.
        """
        raise NotImplementedError
