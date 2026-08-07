"""Telegram Public Web Channel source adapter."""

import re
from datetime import datetime, timezone

import httpx

from pulse.sources.base import BaseSourceAdapter, NewsArticle

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class TelegramChannelAdapter(BaseSourceAdapter):
    """Adapter for public Telegram channels via t.me/s/ web interface."""

    def __init__(
        self,
        source_id: str,
        channel_name: str,
        name: str = "",
        category: str = "ru_hot",
    ) -> None:
        self.source_id = source_id
        self.channel_name = channel_name.lstrip("@")
        self.url = f"https://t.me/s/{self.channel_name}"
        self.name = name or f"Telegram @{self.channel_name}"
        self.category = category

    async def fetch_latest(self) -> list[NewsArticle]:
        """Fetch latest posts from Telegram public web preview.

        Returns:
            list[NewsArticle]: Parsed news articles.
        """
        articles: list[NewsArticle] = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                headers = {"User-Agent": DEFAULT_USER_AGENT}
                resp = await client.get(self.url, headers=headers)
                if resp.status_code != 200:
                    return []

                raw_html = resp.text
                matches = re.findall(
                    r'<div class="tgme_widget_message_text js-message_text[^"]*"[^>]*>(.*?)</div>',
                    raw_html,
                    re.DOTALL,
                )

                for raw_post in matches:
                    clean_text = re.sub(r"<[^>]+>", " ", raw_post)
                    clean_text = " ".join(clean_text.split()).strip()
                    if not clean_text or len(clean_text) < 15:
                        continue

                    # Extract first sentence or first 120 chars as headline
                    parts = clean_text.split(".")
                    headline = parts[0].strip()
                    if len(headline) < 20 and len(parts) > 1:
                        headline = f"{headline}. {parts[1].strip()}"
                    headline = headline[:150]

                    post_url = f"https://t.me/{self.channel_name}"
                    articles.append(
                        NewsArticle(
                            source_id=self.source_id,
                            headline=headline,
                            summary=clean_text[:300],
                            url=post_url,
                            published_at=datetime.now(timezone.utc),
                        )
                    )
        except Exception:
            pass

        return articles
