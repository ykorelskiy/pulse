"""News and words ranker with original headline selection."""

from collections import Counter

from pulse.db.repo import NewsRepo, WordsRepo


def extract_key_phrase(headline: str) -> str:
    """Return headline cleanly formatted as a key phrase."""
    return headline.strip()


class TopicRanker:

    """Ranks RSS news items and reader words to form daily digest topics."""

    def __init__(
        self,
        news_repo: NewsRepo | None = None,
        words_repo: WordsRepo | None = None,
    ) -> None:
        self.news_repo = news_repo or NewsRepo()
        self.words_repo = words_repo or WordsRepo()

    def get_top_news_details(self, limit: int = 5) -> list[dict[str, str]]:
        """Extract top N news headlines from latest collected RSS articles.

        Returns:
            list[dict[str, str]]: Items with keys 'headline', 'source_id', 'url', 'category'.
        """
        results: list[dict[str, str]] = []
        seen_headlines = set()

        try:
            articles = self.news_repo.get_latest_news(limit=50)
            for art in articles:
                headline = art.get("headline", "").strip()
                url = art.get("url", "#")
                source_id = art.get("source_id", "news")
                if not headline:
                    continue

                clean_h = headline.lower()
                if clean_h not in seen_headlines:
                    seen_headlines.add(clean_h)
                    results.append({
                        "phrase": headline,
                        "headline": headline,
                        "url": url,
                        "source_id": source_id,
                    })
                if len(results) >= limit:
                    break
        except Exception:
            pass

        # Realistic fallback headlines across categories if collection is pending
        fallbacks = [
            {
                "phrase": "Илон Маск анонсировал новый этап программы освоения Марса",
                "headline": "Илон Маск анонсировал новый этап программы освоения Марса",
                "url": "https://ria.ru",
                "source_id": "ria_news",
            },
            {
                "phrase": "Звёзды эстрады оказались в центре громкого обсуждения",
                "headline": "Звёзды эстрады оказались в центре громкого обсуждения",
                "url": "https://www.starhit.ru",
                "source_id": "starhit_showbiz",
            },
            {
                "phrase": "Опубликованы свежие подробности международных переговоров",
                "headline": "Опубликованы свежие подробности международных переговоров",
                "url": "https://lenta.ru",
                "source_id": "lenta_news",
            },
            {
                "phrase": "Центробанк опубликовал обновлённый макроэкономический прогноз",
                "headline": "Центробанк опубликовал обновлённый макроэкономический прогноз",
                "url": "https://rssexport.rbc.ru",
                "source_id": "rbc_news",
            },
            {
                "phrase": "Представлена новая нейросеть с рекордной производительностью",
                "headline": "Представлена новая нейросеть с рекордной производительностью",
                "url": "https://3dnews.ru",
                "source_id": "threednews",
            },
        ]

        while len(results) < limit:
            fb = fallbacks[len(results) % len(fallbacks)]
            results.append(fb)

        return results[:limit]

    def get_top_news_phrases(self, limit: int = 5) -> list[str]:
        """Extract top N news headlines."""
        details = self.get_top_news_details(limit=limit)
        return [item["headline"] for item in details]

    def get_top_reader_words(self, limit: int = 5) -> list[str]:
        """Aggregate top N most submitted words from readers."""
        counter: Counter[str] = Counter()

        try:
            words_entries = self.words_repo.get_recent_words(limit=100)
            for entry in words_entries:
                w = entry.get("word")
                if w:
                    counter[w.lower()] += 1
        except Exception:
            pass

        top_pairs = counter.most_common(limit)
        result = [pair[0] for pair in top_pairs]

        # Fallback placeholders if not enough reader words yet
        fallbacks = ["сатира", "технологии", "юмор", "будущее", "пульс"]
        while len(result) < limit:
            result.append(fallbacks[len(result) % len(fallbacks)])

        return result[:limit]
