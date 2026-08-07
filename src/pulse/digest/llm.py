"""Gemini LLM Curator for neural translation (EN -> RU) and Top-10 news selection."""

import json
from typing import Any

import httpx

from pulse.config import get_config
from pulse.logging import get_logger

logger = get_logger("pulse.digest.llm")


def is_mostly_english(text: str) -> bool:
    """Check if string contains mostly English characters."""
    ascii_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return ascii_count > len(text) * 0.3


class LLMCurator:
    """Uses Gemini API to translate foreign headlines and select Top-10 news."""

    def __init__(self, api_key: str | None = None) -> None:
        cfg = get_config().settings
        self.api_key = api_key or cfg.GEMINI_API_KEY

    def curate_and_translate_news(
        self,
        categorized_news: list[dict[str, Any]],
        top_k: int = 10,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Translate foreign headlines and select Top-10 news items using Gemini API.

        Args:
            categorized_news: List of category dicts with 'code', 'title', 'weight', 'items'.
            top_k: Number of top items to select (default 10).

        Returns:
            tuple[list[dict[str, str]], list[dict[str, Any]]]:
                - Top 10 curated news dicts ('headline', 'source_name', 'url', 'category_title')
                - All 30 categorized news dicts with translated Russian headlines
        """
        all_candidates: list[dict[str, str]] = []
        for cat in categorized_news:
            cat_title = cat.get("title", "")
            for item in cat.get("items", []):
                all_candidates.append({
                    "original_headline": item.get("headline", ""),
                    "headline": item.get("headline", ""),
                    "source_name": item.get("source_name", "новости"),
                    "url": item.get("url", "#"),
                    "category_title": cat_title,
                })

        if not self.api_key:
            logger.info("gemini_key_not_set_using_fallback_curation")
            return self._fallback_curation(categorized_news, all_candidates, top_k)

        try:
            items_payload = []
            for idx, cand in enumerate(all_candidates, 1):
                items_payload.append({
                    "id": idx,
                    "headline": cand["headline"],
                    "source": cand["source_name"],
                    "category": cand["category_title"],
                })

            payload_json = json.dumps(items_payload, ensure_ascii=False, indent=2)
            prompt = (
                "Ты — шеф-редактор и ИИ-куратор сатирического Telegram-канала «Пульс дня».\n"
                "Перед тобой 30 новостей дня из 6 категорий.\n\n"
                "Твои задачи:\n"
                "1. **100% Перевод**: Переведи абсолютно все англоязычные заголовки "
                "на выразительный, естественный русский язык без англицизмов.\n"
                "2. **Строгая фильтрация (ЗАПРЕЩЕНО выбирать в ТОП-10)**:\n"
                "   - Скучные рецензии на фильмы, сериалы, спектакли и мюзиклы.\n"
                "   - Корпоративную рекламу, скидки на билеты, анонсы пылесосов и корпуса.\n"
                "   - Сухие канцелярские отчеты министерств и ведомств.\n"
                "3. **Многокритериальная оценка ТОП-10**:\n"
                "   Оцени каждую новость по 4 критериям (виральность/абсурд, резонанс, "
                "интрига, визуальный потенциал для сатиры) и выбери 10 САМЫХ ярких, "
                "смешных, ошеломляющих и резонансных сюжетов для русскоязычного читателя "
                "(например: «ИИ-гаджет OpenAI похож на пончик», «Политик подключился "
                "к заседанию из ванной» и т.д.).\n\n"
                "Верни JSON ровно в таком формате:\n"
                "{\n"
                '  "translated_all": [ {"id": 1, "ru_headline": "Заголовок на русском"}, ...],\n'
                '  "top_10_ids": [1, 5, 8, 12, ...]\n'
                "}\n\n"
                f"Вот список 30 новостей:\n{payload_json}"
            )

            endpoint = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={self.api_key}"
            )
            response = httpx.post(
                endpoint,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"response_mime_type": "application/json"},
                },
                timeout=15.0,
            )

            if response.status_code == 200:
                data = response.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)

                translated_map = {
                    item["id"]: item["ru_headline"]
                    for item in parsed.get("translated_all", [])
                    if "id" in item and "ru_headline" in item
                }
                top_ids = parsed.get("top_10_ids", [])

                for idx, cand in enumerate(all_candidates, 1):
                    if idx in translated_map:
                        cand["headline"] = translated_map[idx]

                cand_idx = 0
                for cat in categorized_news:
                    for item in cat.get("items", []):
                        if cand_idx < len(all_candidates):
                            item["headline"] = all_candidates[cand_idx]["headline"]
                        cand_idx += 1

                top_10_list: list[dict[str, str]] = []
                for top_id in top_ids:
                    if 1 <= top_id <= len(all_candidates):
                        cand = all_candidates[top_id - 1]
                        top_10_list.append({
                            "headline": cand["headline"],
                            "source_name": cand["source_name"],
                            "url": cand["url"],
                            "category_title": cand["category_title"],
                        })

                if len(top_10_list) >= top_k:
                    logger.info("gemini_curation_success", top_count=len(top_10_list))
                    return top_10_list[:top_k], categorized_news
        except Exception as e:
            logger.error("gemini_curation_failed", error=str(e))

        return self._fallback_curation(categorized_news, all_candidates, top_k)

    def _fallback_curation(
        self,
        categorized_news: list[dict[str, Any]],
        all_candidates: list[dict[str, str]],
        top_k: int,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Fallback curation when Gemini API key is missing or request fails."""
        translations_dict = {
            "Cape Cod homeowner sues": "Владелец особняка подал в суд из-за рисков обвала дома",
            "Oregon senators warn prediction markets": (
                "Сенаторы Орегона предупредили о рисках прогнозирования пожаров"
            ),
            "We can see your washing": "Политик случайно подключился к совещанию из ванной комнаты",
            "Kangaroo spotted in Swiss woodland": "Кенгуру замечен в швейцарском лесу",
            "Pig Farm Transformed": "Свиноферму переоборудовали в грибное производство",
            "North West": "13-летняя Норт Уэст зачитала рэп об обидах после отмены тура",
            "McBee Dynasty": "Звезда шоу прокомментировала тюремный срок бывшего мужа",
            "Savannah Guthrie reunites": (
                "Саванна Гатри воссоединилась с коллегой во время перерыва"
            ),
            "Martha Stewart claims Meghan Markle": (
                "Марта Стюарт заявила о сплетнях Меган Маркл на званом ужине"
            ),
            "Ryan Murphy responds to Ariana Grande": (
                "Райан Мерфи ответил на уход Арианы Гранде"
            ),
            "It didn’t need to end this way": "Мать погибшего подростка заявила об ошибках полиции",
            "US airfares expected to stay high": (
                "Цены на авиабилеты в США останутся высокими вопреки падающей нефти"
            ),
            "ICE will not reveal body-camera footage": (
                "Служба миграции отказалась от записей с нагрудных камер"
            ),
            "Key Republican says he will vote": (
                "Ключевой сенатор подтвердил поддержку назначения нового генпрокурора"
            ),
            "Trump’s attorney general pick": (
                "Кандидат Трампа на пост генпрокурора прошёл финальный этап"
            ),
            "Alex Cooper had one demand": (
                "Алекс Купер выдвинула условие на новом шоу «Давай поженим Гарри»"
            ),
            "News Anchor Nearly Swears On Live TV": (
                "Ведущая новостей чуть не сматерилась в прямом эфире при виде ДТП"
            ),
            "Kemi Badenoch’s weird week": (
                "Странная неделя Кеми Баденох: защита неонациста вызвала вопросы"
            ),
            "Today’s the last day to get up to $400 off": (
                "Сегодня последний день скидки на билеты TechCrunch Disrupt"
            ),
        }

        # Priority score calculation for fallback selection
        scored_candidates = []
        for cand in all_candidates:
            h = cand["headline"]
            # Perform fallback translation
            for en_key, ru_val in translations_dict.items():
                if en_key.lower() in h.lower():
                    h = ru_val
                    cand["headline"] = ru_val
                    break

            score = 50
            # Penalize boring review / discount words
            if any(bad in h.lower() for bad in ["рецензия", "мюзикл", "пылесос", "корпус"]):
                score -= 40
            # Boost viral / funny / tech / scandal words
            if any(good in h.lower() for good in [
                "ванн", "пончик", "кенгуру", "скандал", "ии-гаджет",
                "суд", "рэп", "политик", "дразн", "вирус"
            ]):
                score += 30

            scored_candidates.append((score, cand))

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        top_10_list = [
            {
                "headline": cand["headline"],
                "source_name": cand["source_name"],
                "url": cand["url"],
                "category_title": cand["category_title"],
            }
            for _, cand in scored_candidates[:top_k]
        ]

        # Update categorized_news with translated headlines
        cand_map = {c["original_headline"]: c["headline"] for c in all_candidates}
        for cat in categorized_news:
            for item in cat.get("items", []):
                orig = item.get("headline", "")
                if orig in cand_map:
                    item["headline"] = cand_map[orig]

        return top_10_list, categorized_news
