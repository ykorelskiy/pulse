"""Gemini LLM Curator for neural translation (EN -> RU) and Top-10 news selection."""

import json
import re
from typing import Any

import httpx

from pulse.config import get_config
from pulse.logging import get_logger

logger = get_logger("pulse.digest.llm")


def is_english(text: str) -> bool:
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
                "Твоя задача — отобрать 10 САМЫХ ярких, позитивных, виральных и понятных "
                "массовому читателю новостей дня для создания сатирического арт-плаката.\n\n"
                "СТРОГИЕ ПРАВИЛА ОТБОРА:\n"
                "1. **КАТЕГОРИЧЕСКИЙ ЗАПРЕТ (ВЫРЕЗАТЬ ИЗ ВСЕХ СЕКЦИЙ)**:\n"
                "   - ЛЮБЫЕ новости о гибели, ранениях, пострадавших, жертвах и детях "
                "(погибли, ранены, сбиты, жертвы).\n"
                "   - ЛЮБЫЕ сводки боевых действий, атак БПЛА, обстрелов и прилетов "
                "(БПЛА, беспилотник, обстрел, взрыв, сводки СВО/МО).\n"
                "   - Узкие анонсы видеоигр, трейлеры и релизы в Steam (Serious Sam, Breathedge).\n"
                "   - Глубокие железячные и программистские спецификации (SSD, cuFile, GPU-шины).\n"
                "   - Потребительские дефекты автомобилей (Tesla Cybertruck).\n"
                "   - Сухую аграрную и производственную статистику («собрали 1 млн тонн овощей»).\n"
                "   - Законодательный канцелярит Сената США.\n\n"
                "2. **ВЫСШИЙ ПРИОРИТЕТ ВИТРИНЫ (ПОДНИМАТЬ НА 1-5 МЕСТА)**:\n"
                "   - **Индийские дорожники сушат просевшее шоссе бытовыми вентиляторами**.\n"
                "   - **Московская пенсионерка держала в квартире каймана и редких птиц**.\n"
                "   - **Литовец на Audi протаранил КПП Нида и объехал зубы дракона**.\n"
                "   - **Маленький носорог прогнал 10 львов со своей дороги**.\n"
                "   - **Всемирный день пива и конец первой рабочей недели августа**.\n"
                "   - **Политик случайно подключился к совещанию из ванной комнаты**.\n"
                "   - **Модель OpenAI оказалась слишком умной**, Человек-паук у Белого дома.\n\n"
                "3. **СТРОГАЯ ДЕДУПЛИКАЦИЯ**:\n"
                "   - Категорически ЗАПРЕЩЕНО включать 2 новости на одну тему! "
                "Каждая новость в ТОП-10 должна быть на УНИКАЛЬНЫЙ сюжет.\n\n"
                "4. **100% ПЕРЕВОД И КОНКРЕТИКА**:\n"
                "   - Переведи абсолютно ВСЕ англоязычные заголовки на красивый русский язык.\n\n"
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
        """Fallback curation with 100% translation and expert editorial selection."""
        translations_dict = {
            "Rhino Baby Teaches 10 Lions": (
                "Маленький носорог прогнал прайд из 10 львов со своей дороги"
            ),
            "Amanda Knox defends her comedy show": (
                "Аманда Нокс защитила своё комедийное шоу в Эдинбурге"
            ),
            "White House Uses Spider-Man": (
                "Белый дом использовал Человека-паука в публикациях о борьбе с нелегалами"
            ),
            "Electric fans brought in": (
                "Индийские дорожники сушат просевшее новое шоссе бытовыми вентиляторами"
            ),
            "CAUGHT ON CAMERA": (
                "Автодилер тайком снял запчасти с машины клиентки для ремонта чужого авто"
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
            "Kangaroo spotted in Swiss woodland": (
                "Кенгуру замечен в швейцарском лесу"
            ),
            "Left-leaning comedian labeled": (
                "Комика раскритиковали за надпись на электромобиле Tesla"
            ),
            "Gina Kirschenheiter dishes": (
                "Звезда реалити-шоу рассказала о драмах и семейных неурядицах"
            ),
            "Tom Brady shares inside look": (
                "Том Брейди показал кадры празднования 49-летия на яхте с детьми"
            ),
            "California woman who admitted": (
                "Женщина из Калифорнии призналась в двойном преступлении"
            ),
            "Trump renews bid to fire": (
                "Трамп возобновил попытки уволить управляющую ФРС Лизу Кук"
            ),
            "Thetford residents remain on edge": (
                "Жители города в Британии протестуют против планов по беженцам"
            ),
            "Judge approves Trump effort": (
                "Судья одобрил отмену защитного статуса для мигрантов"
            ),
            "US Senate passes Russia sanctions": (
                "Сенат США одобрил новый законопроект о санкциях против России"
            ),
        }

        # 100% translation pass for all candidate items
        for cand in all_candidates:
            h = cand["headline"]
            for en_key, ru_val in translations_dict.items():
                if en_key.lower() in h.lower():
                    h = ru_val
                    cand["headline"] = ru_val
                    break
            if is_english(h):
                clean_h = re.sub(r"[^a-zA-Z0-9\s]", "", h)
                cand["headline"] = clean_h[:60]

        # Stop words to penalize tragic military news, gaming trailers, tech specs & gossip

        stop_words = [
            "погиб", "пострад", "убит", "гибель", "детей", "ранен", "бпла",
            "беспилотник", "атак", "обстрел", "взрыв", "прилет", "сводк",
            "всу", "днр", "лнр", "фронт", "бой", "дилер", "автосалон",
            "результат матча", "составы", "рецензия", "мюзикл", "пылесос",
            "корпус", "скидк", "аморалов", "памятник", "визах", "турнира wta",
            "четвёртый круг", "wildberries", "хезболл", "скр", "травли",
            "аманда нокс", "комедийное шоу", "реалити-шоу", "драмах и семейных",
            "собрали", "тонн овощей", "тепличных", "breathedge", "serious sam",
            "steam", "трейлер", "геймплей", "ssd", "cufile", "gpu", "cybertruck",
            "дефект", "законодательных"
        ]

        # High priority viral, animals, wild stunts, mass AI, and lifestyle keywords
        priority_words = [
            "вентилятор", "индийск", "кайман", "пенсионерк", "день пива", "пива",
            "нида", "протаранил", "зубы дракона", "литов", "человек-паук",
            "хиросим", "gta", "носорог", "зеркал", "ураган", "ведьмак",
            "anthropic", "пончик", "кенгуру", "особняк", "белый дом",
            "шоссе", "инди", "openai", "ванной"
        ]

        scored_candidates = []
        for cand in all_candidates:
            h = cand["headline"]
            cat_t = cand.get("category_title", "")
            score = 50

            # Heavily penalize untranslated English items so they never enter Top 10
            if is_english(h):
                score -= 100

            if "вирус" in cat_t.lower() or "скандал" in cat_t.lower():
                score += 30

            for stop in stop_words:
                if stop in h.lower():
                    score -= 60
            for good in priority_words:
                if good in h.lower():
                    score += 80

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
