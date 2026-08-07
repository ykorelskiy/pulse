"""Unit tests for Telegram bot word validation and rate limiting."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pulse.bot.handlers.word import validate_word
from pulse.bot.middlewares import RateLimitMiddleware


def test_validate_word_valid():
    assert validate_word("сатира") == "сатира"
    assert validate_word("  Нейросеть  ") == "нейросеть"
    assert validate_word("технологический прорыв") == "технологический прорыв"
    assert validate_word("/word Искусственный-интеллект") == "искусственный-интеллект"


def test_validate_word_invalid():
    assert validate_word("ab") is None  # Too short (< 3)
    assert validate_word("a" * 35) is None  # Too long (> 30)
    assert validate_word("слово123") is None  # Contains digits
    assert validate_word("слово 😀") is None  # Contains emoji
    assert validate_word("/word") is None  # Empty command payload



@pytest.mark.asyncio
async def test_rate_limit_middleware_blocks_recent_user():
    mock_words_repo = MagicMock()
    now_iso = datetime.now(timezone.utc).isoformat()
    mock_words_repo.get_recent_words.return_value = [
        {"user_id": 1001, "word": "предыдущее", "created_at": now_iso}
    ]

    middleware = RateLimitMiddleware(words_repo=mock_words_repo)

    handler_mock = AsyncMock()
    event_mock = MagicMock()
    event_mock.from_user.id = 1001
    event_mock.text = "новоеслово"
    event_mock.answer = AsyncMock()

    with patch("pulse.bot.middlewares.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.hour = 12  # Within 00:00 - 18:00 window
        mock_now.strftime.return_value = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        mock_dt.now.return_value.astimezone.return_value = mock_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat

        res = await middleware(handler_mock, event_mock, {})

        assert res is None
        handler_mock.assert_not_called()
        event_mock.answer.assert_called_once()
        assert "уже присылали" in event_mock.answer.call_args[0][0]




@pytest.mark.asyncio
async def test_rate_limit_middleware_allows_new_user():
    mock_words_repo = MagicMock()
    mock_words_repo.get_recent_words.return_value = []

    middleware = RateLimitMiddleware(words_repo=mock_words_repo)

    handler_mock = AsyncMock(return_value="OK")
    event_mock = MagicMock()
    event_mock.from_user.id = 1002
    event_mock.text = "новоеслово"

    with patch("pulse.bot.middlewares.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.hour = 12  # Within 00:00 - 18:00 window
        mock_now.strftime.return_value = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        mock_dt.now.return_value.astimezone.return_value = mock_now

        res = await middleware(handler_mock, event_mock, {})

        assert res == "OK"
        handler_mock.assert_called_once()

