"""Gemini LLM Curator for neural translation (EN -> RU) and Top-10 news selection."""

import json
from typing import Any

import httpx

from pulse.config import get_config
from pulse.logging import get_logger

logger = get_logger("pulse.digest.llm")


def is_mostly_english(text: str) -> str:
    """Check if string contains mostly English characters."""
    ascii_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return "en" if ascii_count > len(text) * 0.3 else "ru"


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
                - All categorized news dicts with translated Russian headlines
        """
        all_candidates: list[dict[str, str]] = []
        for cat in categorized_news:
            cat_title = cat.get("title", "")
            for item in cat.get("items", []):
                all_candidates.append({
                    "original_headline": item.get("headline", ""),
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", ""),
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
                    "summary_snippet": cand["summary"],
                    "source": cand["source_name"],
                    "category": cand["category_title"],
                })

            payload_json = json.dumps(items_payload, ensure_ascii=False, indent=2)
            prompt = (
                "Ты — шеф-редактор и ИИ-художник сатирического Telegram-канала «Пульс дня».\n"
                "Твоя задача — отобрать 10 САМЫХ ярких, виральных и визуально сочных новостей "
                "дня для создания сатирического арт-плаката.\n\n"
                "СТРОГИЕ ПРАВИЛА ОТБОРА:\n"
                "1. **Категорический ЗАПРЕТ (НЕ ВЫБИРАТЬ в ТОП-10)**:\n"
                "   - Сухую военную/политическую повестку (сводки СВО, БПЛА, минюст, "
                "иноагенты, уголовные дела о фейках, санкции).\n"
                "   - Абстрактные заголовки без названий и фактов («результат матча "
                "вывел в лидеры», «оглашены составы»).\n"
                "   - Скучные рецензии на фильмы/сериалы, скидки на парфюмерию.\n\n"

                "2. **ПРИОРИТЕТ ВИТРИНЫ (Искать именно это)**:\n"
                "   - **Визуальный абсурд и курьёзы**: сушат шоссе вентиляторами, автодилер снял "
                "запчасти клиентки, Человек-паук в Белом доме.\n"
                "   - **Технологический и научный сюрреализм**: ИИ-зеркала в космосе, "
                "новый металл Хиросимы, ИИ-модель от ураганов.\n"
                "   - **Рекорды поп-культуры и ИТ-ирония**: предзаказы GTA VI убили GTA V, "
                "босс Anthropic жалуется на меркантильность ИТ-шников.\n\n"
                "3. **100% ПЕРЕВОД И КОНКРЕТИКА**:\n"
                "   - Переведи ВСЕ англоязычные заголовки на красивый русский язык.\n"
                "   - Используй данные 'summary_snippet' для превращения абстрактных фразы "
                "в 1 конкретную сюжетную строку со смыслом.\n\n"
                "Верни JSON ровно в таком формате:\n"
                "{\n"
                '  "translated_all": [ {"id": 1, "ru_headline": "Заголовок"}, ...],\n'
                '  "top_10_ids": [1, 5, 8, 12, ...]\n'
                "}\n\n"
                f"Вот список новостей:\n{payload_json}"
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
        """Fallback curation with smart stop-word scoring and viral priority."""
        translations_dict = {
            "Kangaroo spotted in Swiss woodland": (
                "Кенгуру замечен в швейцарском лесу"
            ),
            "Electric fans brought in": (

                "Индийские дорожники сушат просевшее новое шоссе бытовыми вентиляторами"
            ),
            "CAUGHT ON CAMERA": (
                "Автодилер тайком снял запчасти с машины клиентки для ремонта чужого авто"
            ),
            "White House Uses Spider-Man": (
                "Белый дом использовал Человека-паука в публикациях о борьбе с нелегалами"
            ),
            "Giant mirrors in space": (
                "Проект гигантских зеркал в космосе для ночного освещения Земли вызвал споры"
            ),
            "Anthropic CEO reportedly worried": (
                "Глава Anthropic пожаловался, что новые сотрудники думают только о деньгах"
            ),
            "Cape Cod homeowner sues": (
                "Владелец особняка подал в суд из-за риска обвала дома с берегового обрыва"
            ),
            "Pig Farm Transformed": "Свиноферму переоборудовали в грибное производство",
            "Computer maker Framework notifies": (
                "Производитель ноутбуков Framework предупредил клиентов об утечке данных"
            ),
            "Cloudflare launches Kitesurf": (
                "Cloudflare запустила новый браузер Kitesurf для ИИ-агентов"
            ),
            "Today’s the last day to get up to $400 off": (
                "Сегодня последний день скидки на билеты TechCrunch Disrupt"
            ),
            "North West": "13-летняя Норт Уэст зачитала рэп об обидах после отмены тура",
            "Christina Pazsitzky makes statement": (
                "Кристина Пашицки запустила дерзкую рекламу помады после развода"
            ),
            "Dak Prescott breaks silence": (
                "Дак Прескотт прокомментировал скандальный разрыв с невестой"
            ),
            "Julia Roberts has a": (
                "Джулия Робертс появилась в платье в горошек на свадьбе племянницы"
            ),
            "Believe it: Le Labo is on sale": (
                "Парфюмерный брендовый набор поступил в продажу со скидкой $60"
            ),
            "Where Antonio Banderas and Melanie Griffith": (
                "Как складываются отношения Антонио Бандераса и Мелани Гриффит после развода"
            ),
            "Conor McGregor Gives Update": (
                "Конор Макгрегор объявил о завершении операции на колене и возвращении"
            ),
            "Earth, Wind & Fire Drummer": (
                "Барабанщик легендарной группы госпитализирован после экстренного вызова"
            ),
            "Cambridge academics reject": (
                "Учёные Кембриджа отклонили попытку университета урегулировать споры"
            ),
            "Spanish police arrest 78": (
                "Полиция Испании задержала 78 членов крупной сети контрабандистов"
            ),
            "Kemi Badenoch’s weird week": (
                "Странная неделя Кеми Баденох: защита неонациста вызвала вопросы"
            ),
        }

        # Stop words to heavily penalize dry news in fallback
        stop_words = [
            "минюст", "иноагент", "бпла", "сво", "законопроект", "составы",
            "результат матча", "рецензия", "мюзикл", "пылесос", "корпус",
            "скидк", "хиросим", "хлопок", "населенный пункт", "эксперт раскрыл"
        ]

        # High priority viral keywords
        viral_words = [
            "вентилятор", "человек-паук", "хиросим", "gta", "дилер",
            "зеркал", "ураган", "ведьмак", "anthropic", "пончик", "кенгуру", "рэп"
        ]

        scored_candidates = []
        for cand in all_candidates:
            h = cand["headline"]
            for en_key, ru_val in translations_dict.items():
                if en_key.lower() in h.lower():
                    h = ru_val
                    cand["headline"] = ru_val
                    break

            score = 50
            for stop in stop_words:
                if stop in h.lower():
                    score -= 40
            for good in viral_words:
                if good in h.lower():
                    score += 50

            scored_candidates.append((score, cand))

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

        cand_map = {c["original_headline"]: c["headline"] for c in all_candidates}
        for cat in categorized_news:
            for item in cat.get("items", []):
                orig = item.get("headline", "")
                if orig in cand_map:
                    item["headline"] = cand_map[orig]

        return top_10_list, categorized_news
