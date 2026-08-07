"""Base interface for news sources."""

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class NewsArticle(BaseModel):
    """News article data transfer object."""

    source_id: str
    headline: str
    url: str
    published_at: datetime | None = None


class BaseSourceAdapter(ABC):
    """Abstract adapter interface for news feed sources."""

    @abstractmethod
    async def fetch_latest(self) -> list[NewsArticle]:
        """Fetch latest news items from source feed.

        Returns:
            list[NewsArticle]: List of fetched news articles.
        """
        raise NotImplementedError
