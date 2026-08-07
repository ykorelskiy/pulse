"""Unit tests for RSS news collection and registry."""

from unittest.mock import MagicMock, patch

import pytest

from pulse.sources.registry import SourceRegistry
from pulse.sources.rss import RSSSourceAdapter


@pytest.mark.asyncio
async def test_rss_adapter_parses_feed():
    mock_feed = MagicMock()
    mock_entry1 = MagicMock()
    mock_entry1.title = "Тестовая новость 1"
    mock_entry1.link = "https://example.com/news/1"
    mock_entry1.published_parsed = (2026, 8, 7, 12, 0, 0, 4, 219, 0)

    mock_entry2 = MagicMock()
    mock_entry2.title = "Тестовая новость 2"
    mock_entry2.link = "https://example.com/news/2"
    mock_entry2.published_parsed = None
    mock_entry2.updated_parsed = None

    mock_feed.entries = [mock_entry1, mock_entry2]

    with patch("feedparser.parse", return_value=mock_feed):
        adapter = RSSSourceAdapter(source_id="test_src", feed_url="http://rss.com")
        articles = await adapter.fetch_latest()

        assert len(articles) == 2
        assert articles[0].headline == "Тестовая новость 1"
        assert articles[0].url == "https://example.com/news/1"
        assert articles[0].source_id == "test_src"


def test_source_registry_loads_config():
    registry = SourceRegistry.load_from_config()
    adapters = registry.get_all()
    assert len(adapters) == 3
    source_ids = [a.source_id for a in adapters]
    assert "rbc_news" in source_ids
