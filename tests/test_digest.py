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
    items = [
        {"id": "1", "headline": "Запуск нового ИИ корабля", "status": "scored", "source_id": "lenta_news", "virality": 8, "relevance": 5, "significance": 4},
        {"id": "2", "headline": "Рекордные показатели экономики", "status": "scored", "source_id": "life_news", "virality": 7, "relevance": 4, "significance": 3},
        {"id": "3", "headline": "Открытие суперкомпьютера", "status": "scored", "source_id": "mash_telegram", "virality": 9, "relevance": 5, "significance": 5},
        {"id": "4", "headline": "Фестиваль робототехники", "status": "scored", "source_id": "techcrunch", "virality": 6, "relevance": 4, "significance": 3},
        {"id": "5", "headline": "Новый спутник связи", "status": "scored", "source_id": "baza_telegram", "virality": 8, "relevance": 5, "significance": 4},
    ]
    mock_news_repo.get_latest_news.return_value = items
    mock_news_repo.get_scored_24h_news.return_value = items




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
    assert any("Запуск" in p for p in phrases)
    assert len(words) == 5
    assert words[0] == "сатира"

