"""Unit tests for news phrase extraction and TopicRanker."""

from unittest.mock import MagicMock

from pulse.digest.ranker import TopicRanker, extract_key_phrase


def test_extract_key_phrase():
    res1 = extract_key_phrase("Илон Маск заявляет о возвращении фабрики")
    assert "Илон" in res1
    assert "Маск" in res1

    res2 = extract_key_phrase("Сборная побеждает в турнире")
    assert "Сборная" in res2


def test_topic_ranker_phrases_fallback(mock_supabase):
    mock_news_repo = MagicMock()
    mock_news_repo.get_latest_news.return_value = [
        {"headline": "Запуск нового ИИ корабля"},
        {"headline": "Рекордные показатели экономики"},
    ]

    mock_words_repo = MagicMock()
    mock_words_repo.get_recent_words.return_value = [
        {"word": "сатира"},
        {"word": "сатира"},
        {"word": "будущее"},
    ]

    ranker = TopicRanker(news_repo=mock_news_repo, words_repo=mock_words_repo)

    phrases = ranker.get_top_news_phrases(limit=5)
    words = ranker.get_top_reader_words(limit=5)

    assert len(phrases) == 5
    assert "Запуск нового ИИ корабля" in phrases[0] or "Запуск" in phrases[0]
    assert len(words) == 5
    assert words[0] == "сатира"
