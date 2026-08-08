"""Source registry loader."""

from pulse.config import get_config
from pulse.sources.base import BaseSourceAdapter
from pulse.sources.rss import RSSSourceAdapter, CalendRuAdapter
from pulse.sources.telegram_web import TelegramChannelAdapter


class SourceRegistry:
    """Registry managing active news source adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseSourceAdapter] = {}

    def register(self, adapter: BaseSourceAdapter) -> None:
        """Register a new source adapter instance."""
        self._adapters[adapter.source_id] = adapter

    def get_all(self) -> list[BaseSourceAdapter]:
        """Get all registered source adapters."""
        return list(self._adapters.values())

    @classmethod
    def load_from_config(cls) -> "SourceRegistry":
        """Factory method loading active sources from yaml configuration."""
        registry = cls()
        cfg = get_config()
        for item in cfg.sources.sources:
            if item.get("enabled", True):
                stype = item.get("type", "rss")
                if stype == "telegram" or "channel_name" in item:
                    adapter = TelegramChannelAdapter(
                        source_id=item["id"],
                        channel_name=item.get("channel_name", item.get("url", "")),
                        name=item.get("name", item["id"]),
                        category=item.get("category", "ru_hot"),
                    )
                else:
                    if item["id"] == "calend_ru":
                        adapter = CalendRuAdapter(
                            source_id=item["id"],
                            feed_url=item["url"],
                            name=item.get("name", item["id"]),
                            category=item.get("category", "lifestyle"),
                        )
                    else:
                        adapter = RSSSourceAdapter(
                            source_id=item["id"],
                            feed_url=item["url"],
                            name=item.get("name", item["id"]),
                            category=item.get("category", "general"),
                        )
                registry.register(adapter)

        return registry
