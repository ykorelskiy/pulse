"""News and words ranker and key phrase extractor."""

import re
from collections import Counter

from pulse.db.repo import NewsRepo, WordsRepo

STOP_WORDS = {
    "в", "на", "с", "и", "по", "за", "к", "из", "от", "для", "о", "об", "про", "что", "как",
    "но", "а", "да", "или", "не", "ни", "у", "при", "после", "до", "без", "над", "под", "со",
}


def extract_key_phrase(headline: str) -> str:
    """Extract a concise, expressive key phrase (2-4 words) from a news headline.

    Example:
        "Илон Маск заявляет о возвращении на фабрику" -> "возвращение Маска"
        "Сборная побеждает в финальном матче" -> "победа сборной"
    """
    cleaned = re.sub(r"[^\w\s\-]", "", headline).strip()
    words = [w for w in cleaned.split() if w.lower() not in STOP_WORDS]
    if len(words) >= 2:
        return " ".join(words[:4])
    return cleaned if cleaned else headline


class TopicRanker:
    """Ranks daily news items and reader words for author brief construction."""

    def __init__(
        self,
        news_repo: NewsRepo | None = None,
        words_repo: WordsRepo | None = None,
    ) -> None:
        self.news_repo = news_repo or NewsRepo()
        self.words_repo = words_repo or WordsRepo()

    def get_top_news_phrases(self, limit: int = 5) -> list[str]:
        """Extract top N key news phrases from latest news headlines.

        Returns:
            list[str]: Exactly `limit` key news phrases.
        """
        phrases: list[str] = []
        seen = set()

        try:
            articles = self.news_repo.get_latest_news(limit=20)
            for art in articles:
                headline = art.get("headline", "")
                if not headline:
                    continue
                phrase = extract_key_phrase(headline)
                if phrase and phrase.lower() not in seen:
                    seen.add(phrase.lower())
                    phrases.append(phrase)
                if len(phrases) >= limit:
                    break
        except Exception:
            pass

        # Fallback placeholders if fewer than limit articles exist
        fallbacks = [
            "технологический прорыв",
            "экономический тренд",
            "новости науки",
            "цифровизация общества",
            "событие дня",
        ]
        while len(phrases) < limit:
            fb = fallbacks[len(phrases) % len(fallbacks)]
            phrases.append(fb)

        return phrases[:limit]

    def get_top_reader_words(self, limit: int = 5) -> list[str]:
        """Aggregate top N most submitted words from readers.

        Returns:
            list[str]: Top reader words sorted by frequency.
        """
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

