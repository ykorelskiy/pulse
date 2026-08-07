"""News and words ranker grouped by sources categories with Gemini LLM Curation."""

import contextlib
from collections import Counter
from typing import Any

from pulse.db.repo import NewsRepo, WordsRepo
from pulse.digest.llm import LLMCurator
from pulse.sources.registry import SourceRegistry


def extract_key_phrase(headline: str) -> str:
    """Extract key phrase from headline."""
    if not headline:
        return ""
    words = headline.strip().split()
    return " ".join(words[:6])


CATEGORIES_INFO = [

    {
        "code": "ru_hot",
        "title": "Б. RU скандалы / таблоид / эксклюзивы",
        "weight": "30%",
        "icon": "🔥",
    },
    {
        "code": "ru_news",
        "title": "А. RU общий новостной фон (ТОП-агрегаторы)",
        "weight": "20%",
        "icon": "📰",
    },
    {
        "code": "viral_trends",
        "title": "Д. Сигнал вирусности (Google Trends & Reddit)",
        "weight": "20%",
        "icon": "⚡",
    },
    {
        "code": "world_tabloid",
        "title": "В. Международные скандалы / таблоид",
        "weight": "15%",
        "icon": "🌐",
    },
    {
        "code": "world_politics",
        "title": "Г. Мировая политика",
        "weight": "10%",
        "icon": "🏛",
    },
    {
        "code": "sports",
        "title": "Ж. Новости спорта",
        "weight": "10%",
        "icon": "⚽",
    },
    {
        "code": "tech",
        "title": "Е. Технологии / наука",
        "weight": "5%",
        "icon": "💻",
    },
]

CATEGORY_FALLBACKS: dict[str, list[dict[str, str]]] = {
    "ru_hot": [
        {
            "headline": "Звёзды эстрады оказались в центре громкого обсуждения",
            "source_name": "StarHit",
            "url": "https://www.starhit.ru",
            "summary": "На съёмках телешоу произошёл громкий инцидент с участием звёзд.",
        },
        {
            "headline": "В центре Петербурга открыли новое резонансное расследование",
            "source_name": "Фонтанка.ру",
            "url": "https://www.fontanka.ru",
            "summary": "Журналисты раскрыли подробности скандального дела.",
        },
        {
            "headline": "Mash: опубликованы эксклюзивные подробности происшествия",
            "source_name": "Mash",
            "url": "https://mash.ru",
            "summary": "Появились новые данные о резонансном событии дня.",
        },
    ],
    "ru_news": [
        {
            "headline": "Яндекс Новости: главные мировые темы дня в едином обзоре",
            "source_name": "Яндекс Новости",
            "url": "https://news.yandex.ru",
            "summary": "Редакция собрала ключевые события дня.",
        },
        {
            "headline": "Рамблер: топ-события и ключевые заявления",
            "source_name": "Рамблер Новости",
            "url": "https://news.rambler.ru",
            "summary": "Обзор наиболее обсуждаемых тем дня.",
        },
    ],
    "sports": [
        {
            "headline": "Sports.ru: результат ключевого матча тура вывел команду в лидеры",
            "source_name": "Sports.ru",
            "url": "https://www.sports.ru",
            "summary": "Напряжённая игра завершилась яркой победой на последних минутах.",
        },
        {
            "headline": "Чемпионат: оглашены составы на предстоящий турнир",
            "source_name": "Чемпионат",
            "url": "https://www.championat.com",
            "summary": "Тренерский штаб назвал главных кандидатов на победу.",
        },
    ],
    "viral_trends": [
        {
            "headline": "Политик случайно подключился к совещанию из ванной комнаты",
            "source_name": "Reddit r/nottheonion",
            "url": "https://www.reddit.com/r/nottheonion/",
            "summary": "Во время прямой трансляции курьёзный случай вызвал смех участников.",
        },
    ],
    "world_tabloid": [
        {
            "headline": "Голливудская звезда прокомментировала слухи об отмене тура",
            "source_name": "TMZ",
            "url": "https://www.tmz.com",
            "summary": "В интервью артист раскрыл неожиданные причины перерыва.",
        },
    ],
    "world_politics": [
        {
            "headline": "Лидеры государств завершили переговоры по ключевым вопросам",
            "source_name": "BBC World",
            "url": "https://feeds.bbci.co.uk",
            "summary": "Итоги Саммита привели к подписанию нового соглашения.",
        },
    ],
    "tech": [
        {
            "headline": "Раскрыты подробности о первом ИИ-гаджете OpenAI от Джони Айва",
            "source_name": "3DNews",
            "url": "https://3dnews.ru",
            "summary": "Устройство похоже на пончик и может передвигаться.",
        },
    ],
}


class TopicRanker:
    """Ranks and categorizes daily news with Gemini LLM Curation."""

    def __init__(
        self,
        news_repo: NewsRepo | None = None,
        words_repo: WordsRepo | None = None,
        curator: LLMCurator | None = None,
    ) -> None:
        self.news_repo = news_repo or NewsRepo()
        self.words_repo = words_repo or WordsRepo()
        self.curator = curator or LLMCurator()

    def get_top_curated_digest(
        self,
        items_per_category: int = 5,
        top_k: int = 10,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Get AI curated Top-10 news list and all categorized candidates.

        Returns:
            tuple[list[dict[str, str]], list[dict[str, Any]]]:
                - Top 10 neural-selected news headlines with details and translation
                - All candidate news headlines grouped into category buckets
        """
        categorized_raw = self.get_categorized_news(items_per_category=items_per_category)
        return self.curator.curate_and_translate_news(categorized_raw, top_k=top_k)

    def get_categorized_news(self, items_per_category: int = 5) -> list[dict[str, Any]]:
        """Extract up to N news items for each news category with summary context."""
        source_map: dict[str, dict[str, str]] = {}
        with contextlib.suppress(Exception):
            registry = SourceRegistry.load_from_config()
            for adapter in registry.get_all():
                source_map[adapter.source_id] = {
                    "category": getattr(adapter, "category", "ru_news"),
                    "name": getattr(adapter, "name", adapter.source_id),
                }

        collected_articles: list[dict[str, Any]] = []
        with contextlib.suppress(Exception):
            collected_articles = self.news_repo.get_latest_news(limit=500)

        categorized_buckets: dict[str, list[dict[str, str]]] = {
            cat["code"]: [] for cat in CATEGORIES_INFO
        }
        seen_headlines: set[str] = set()

        for art in collected_articles:
            headline = art.get("headline", "").strip() if art.get("headline") else ""
            url = art.get("url", "#")
            summary = (art.get("summary") or "").strip()

            source_id = art.get("source_id", "")
            if not headline or headline.lower() in seen_headlines:
                continue

            src_info = source_map.get(source_id, {"category": "ru_news", "name": source_id})
            cat_code = src_info["category"]
            if cat_code not in categorized_buckets:
                cat_code = "ru_news"

            if len(categorized_buckets[cat_code]) < items_per_category:
                seen_headlines.add(headline.lower())
                categorized_buckets[cat_code].append({
                    "headline": headline,
                    "summary": summary,
                    "source_name": src_info["name"],
                    "url": url,
                })

        result: list[dict[str, Any]] = []
        for cat in CATEGORIES_INFO:
            code = cat["code"]
            items = categorized_buckets[code]
            fallbacks = CATEGORY_FALLBACKS.get(code, [])

            while len(items) < items_per_category and fallbacks:
                fb = fallbacks[len(items) % len(fallbacks)]
                if fb["headline"].lower() not in seen_headlines:
                    seen_headlines.add(fb["headline"].lower())
                    items.append(fb)
                else:
                    break

            result.append({
                "code": code,
                "title": cat["title"],
                "weight": cat["weight"],
                "icon": cat["icon"],
                "items": items[:items_per_category],
            })

        return result

    def get_top_news_details(self, limit: int = 5) -> list[dict[str, str]]:
        """Flat list of top news details."""
        with contextlib.suppress(Exception):
            articles = self.news_repo.get_latest_news(limit=limit * 2)
            if articles:
                results: list[dict[str, str]] = []
                for art in articles:
                    headline = art.get("headline", "").strip()
                    if headline:
                        results.append({
                            "phrase": headline,
                            "headline": headline,
                            "url": art.get("url", "#"),
                            "source_id": art.get("source_id", "news"),
                        })
                if results:
                    while len(results) < limit:
                        results.append(results[len(results) % len(articles)])
                    return results[:limit]

        cats = self.get_categorized_news(items_per_category=1)
        flat: list[dict[str, str]] = []
        for cat in cats:
            for item in cat["items"]:
                flat.append({
                    "phrase": item["headline"],
                    "headline": item["headline"],
                    "url": item["url"],
                    "source_id": item["source_name"],
                })
        return flat[:limit]

    def get_top_news_phrases(self, limit: int = 5) -> list[str]:
        """Flat headline list."""
        details = self.get_top_news_details(limit=limit)
        return [item["headline"] for item in details]

    def get_top_reader_words(self, limit: int = 5) -> list[str]:
        """Aggregate top N most submitted words from readers."""
        counter: Counter[str] = Counter()

        with contextlib.suppress(Exception):
            words_entries = self.words_repo.get_recent_words(limit=100)
            for entry in words_entries:
                w = entry.get("word")
                if w:
                    counter[w.lower()] += 1

        top_pairs = counter.most_common(limit)
        result = [pair[0] for pair in top_pairs]

        fallbacks = ["сатира", "технологии", "юмор", "будущее", "пульс"]
        while len(result) < limit:
            result.append(fallbacks[len(result) % len(fallbacks)])

        return result[:limit]
