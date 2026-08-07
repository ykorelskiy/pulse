"""News and words ranker grouped by 6 sources categories."""

import contextlib
from collections import Counter
from typing import Any

from pulse.db.repo import NewsRepo, WordsRepo
from pulse.sources.registry import SourceRegistry

CATEGORIES_INFO = [
    {
        "code": "ru_hot",
        "title": "Б. RU скандалы / таблоид",
        "weight": "30%",
        "icon": "🔥",
    },
    {
        "code": "ru_news",
        "title": "А. RU общий новостной фон",
        "weight": "20%",
        "icon": "📰",
    },
    {
        "code": "viral_trends",
        "title": "Д. Сигнал вирусности (Google Trends)",
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
        },
        {
            "headline": "Известный артист прокомментировал резонансный инцидент",
            "source_name": "7Дней.ру",
            "url": "https://7days.ru",
        },
        {
            "headline": "В центре столицы произошло громкое происшествие",
            "source_name": "Комсомольская правда",
            "url": "https://www.kp.ru",
        },
        {
            "headline": "Скандал на съёмках нового шоу вызвал бурные споры",
            "source_name": "StarHit",
            "url": "https://www.starhit.ru",
        },
        {
            "headline": "Популярный блогер заявил о неожиданном решении",
            "source_name": "7Дней.ру",
            "url": "https://7days.ru",
        },
    ],
    "ru_news": [
        {
            "headline": "Центробанк опубликовал обновлённый макроэкономический прогноз",
            "source_name": "РБК",
            "url": "https://rssexport.rbc.ru",
        },
        {
            "headline": "Опубликованы новые подробности межведомственных переговоров",
            "source_name": "Лента.ру",
            "url": "https://lenta.ru",
        },
        {
            "headline": "Госдума рассмотрела новый пакет законопроектов",
            "source_name": "РИА Новости",
            "url": "https://ria.ru",
        },
        {
            "headline": "Минфин представил отчет о доходах и расходах бюджета",
            "source_name": "Коммерсантъ",
            "url": "https://www.kommersant.ru",
        },
        {
            "headline": "ТАСС: утверждены новые региональные инициативы",
            "source_name": "ТАСС",
            "url": "https://tass.ru",
        },
    ],
    "viral_trends": [
        {
            "headline": "Резкий скачок поисковых запросов в трендах дня",
            "source_name": "Google Trends RU",
            "url": "https://trends.google.com",
        },
        {
            "headline": "Обсуждаемая публикация на r/nottheonion набрала тысячи откликов",
            "source_name": "Reddit",
            "url": "https://www.reddit.com/r/nottheonion/",
        },
        {
            "headline": "Вирусный мемориальный тренд охватил соцсети",
            "source_name": "Google Trends RU",
            "url": "https://trends.google.com",
        },
        {
            "headline": "Абсурдная новость дня стала лидером обсуждений в сети",
            "source_name": "Reddit",
            "url": "https://www.reddit.com",
        },
        {
            "headline": "Пользователи массово ищут подробности необычного явления",
            "source_name": "Google Trends RU",
            "url": "https://trends.google.com",
        },
    ],
    "world_tabloid": [
        {
            "headline": "Голливудская звезда замечена на закрытой вечеринке",
            "source_name": "TMZ",
            "url": "https://www.tmz.com",
        },
        {
            "headline": "Эксклюзивные подробности личной жизни знаменитостей",
            "source_name": "Page Six",
            "url": "https://pagesix.com",
        },
        {
            "headline": "Громкое расставание пары из шоу-бизнеса потрясло фанатов",
            "source_name": "The Hollywood Gossip",
            "url": "https://feeds.thehollywoodgossip.com",
        },
        {
            "headline": "Неожиданное заявление продюсера об очередном скандале",
            "source_name": "TMZ",
            "url": "https://www.tmz.com",
        },
        {
            "headline": "Светский выходы и модные конфузы недели",
            "source_name": "Page Six",
            "url": "https://pagesix.com",
        },
    ],
    "world_politics": [
        {
            "headline": "BBC: Состоялся очередной раунд международных консультаций",
            "source_name": "BBC News World",
            "url": "https://www.bbc.com/news/world",
        },
        {
            "headline": "The Guardian: Саммит глав государств завершился итоговым коммюнике",
            "source_name": "The Guardian",
            "url": "https://www.theguardian.com/world",
        },
        {
            "headline": "Международная комиссия опубликовала ежегодный доклады",
            "source_name": "BBC News World",
            "url": "https://www.bbc.com/news/world",
        },
        {
            "headline": "Дипломатический демарш вызвал обсуждение в ООН",
            "source_name": "The Guardian",
            "url": "https://www.theguardian.com/world",
        },
        {
            "headline": "Лидеры европейских стран выступили с совместным заявлением",
            "source_name": "BBC News World",
            "url": "https://www.bbc.com/news/world",
        },
    ],
    "tech": [
        {
            "headline": "ИИ впервые создал жизнеспособные биологические конструкции",
            "source_name": "3DNews",
            "url": "https://3dnews.ru",
        },
        {
            "headline": "Хабр: Разработчики анонсировали новый фреймворк для ИИ",
            "source_name": "Хабр",
            "url": "https://habr.com",
        },
        {
            "headline": "TechCrunch: Крупная сделка в сфере полупроводников и нейросетей",
            "source_name": "TechCrunch",
            "url": "https://techcrunch.com",
        },
        {
            "headline": "Раскрыты подробности о первом персональном гаджете нового поколения",
            "source_name": "3DNews",
            "url": "https://3dnews.ru",
        },
        {
            "headline": "Исследователи представили новый квантовый алгоритм",
            "source_name": "Хабр",
            "url": "https://habr.com",
        },
    ],
}


def extract_key_phrase(headline: str) -> str:
    """Return headline cleanly formatted as a key phrase."""
    return headline.strip()


class TopicRanker:
    """Ranks RSS news items by category and reader words."""

    def __init__(
        self,
        news_repo: NewsRepo | None = None,
        words_repo: WordsRepo | None = None,
    ) -> None:
        self.news_repo = news_repo or NewsRepo()
        self.words_repo = words_repo or WordsRepo()

    def get_categorized_news(self, items_per_category: int = 5) -> list[dict[str, Any]]:
        """Extract up to N news items for each of the 6 news categories.

        Returns:
            list[dict[str, Any]]: List of categories with metadata and headline items.
        """
        source_map: dict[str, dict[str, str]] = {}
        try:
            registry = SourceRegistry.load_from_config()
            for adapter in registry.get_all():
                source_map[adapter.source_id] = {
                    "category": getattr(adapter, "category", "ru_news"),
                    "name": getattr(adapter, "name", adapter.source_id),
                }
        except Exception:
            pass

        # Fetch recent news pool
        collected_articles: list[dict[str, Any]] = []
        with contextlib.suppress(Exception):
            collected_articles = self.news_repo.get_latest_news(limit=500)


        categorized_buckets: dict[str, list[dict[str, str]]] = {
            cat["code"]: [] for cat in CATEGORIES_INFO
        }
        seen_headlines: set[str] = set()

        for art in collected_articles:
            headline = art.get("headline", "").strip()
            url = art.get("url", "#")
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
                    "source_name": src_info["name"],
                    "url": url,
                })

        # Top up any category with fallbacks if RSS collection yielded < items_per_category
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

        fallbacks = ["сатира", "технологии", "юмор", "будущее", "пульс"]
        while len(result) < limit:
            result.append(fallbacks[len(result) % len(fallbacks)])

        return result[:limit]
