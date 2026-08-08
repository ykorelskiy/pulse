"""Gemini LLM Curator for micro-batch neural evaluation and translation."""

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


VICTIMS_KEYWORDS = [
    "погиб", "пострад", "убит", "гибель", "ранен", "жертв", "убийств",
    "крушени", "авари", "рухнул", "катастроф", "пожар"
]

PRIORITY_VIRAL_KEYWORDS = [
    "вентилятор", "индийск", "кайман", "пенсионерк", "день пива", "пива",
    "протаранил", "зубы дракона", "человек-паук",
    "gta", "носорог", "зеркал", "ведьмак",
    "anthropic", "пончик", "кенгуру", "особняк",
    "шоссе", "инди", "openai", "ванной"
]


class LLMCurator:
    """Uses Gemini API to evaluate news items in micro-batches and score them."""

    def __init__(self, api_key: str | None = None) -> None:
        cfg = get_config().settings
        self.api_key = api_key or cfg.GEMINI_API_KEY

    def score_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Evaluate a micro-batch of up to 20 news items using Gemini API.

        Args:
            items: List of dicts with 'id', 'headline', 'summary', 'source_id', etc.

        Returns:
            List of dicts with keys:
            - 'id': item identifier
            - 'ru_headline': translated/adapted title in Russian
            - 'has_victims': bool (hard filter)
            - 'relevance': int 1-5
            - 'comedic_potential': int 1-5
            - 'significance': int 1-5
            - 'tone': int -1, 0, 1
        """
        if not items:
            return []

        if not self.api_key:
            logger.info("gemini_key_not_set_using_heuristic_batch_scoring")
            return self._heuristic_batch_scoring(items)

        payload = [
            {
                "id": str(item.get("id", idx)),
                "headline": item.get("headline", item.get("headline_original", "")),
                "summary": item.get("summary", ""),
                "source": item.get("source_id", "новости"),
            }
            for idx, item in enumerate(items, 1)
        ]

        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

        prompt = (
            "Ты — главный редактор сатирического издания «Пульс дня».\n"
            "Оцени список новостей по жестким критериям для формирования суточного ТОПа.\n\n"
            "КРИТЕРИИ ОЦЕНКИ:\n"
            "1. `ru_headline`: Заголовок на красивом грамотном русском языке. ОБЯЗАТЕЛЬНО ПЕРЕВЕДИ англоязычные заголовки (100% перевод)!\n"
            "2. `has_victims` (boolean): ЭМОЦИОНАЛЬНОЕ ВОЗДЕЙСТВИЕ И НАСТРОЕНИЕ:\n"
            "   Задай себе главный вопрос: «Эта новость поднимает настроение или ухудшает настроение у 9 из 10 обычных читателей?»\n"
            "   - Если новость ухудшает настроение (смерти, гибель людей, тяжелые болезни, бытовой депрессивный негатив, несчастные случаи, трагедии) -> true (ОТСЕЧЬ из выпуска).\n"
            "   - Если новость поднимает настроение, смешит, вдохновляет или рассказывает о позитивном спасении, победе или прорыве в науке -> false (ПРОПУСТИТЬ в выпуск).\n"
            "3. `relevance` (1-5): Насколько новость интересна и понятна массовому читателю из РФ и СНГ.\n"
            "4. `significance` (1-5): Глобальный или общенациональный масштаб события.\n"
            "5. `virality` (-10..+10): ВИРАЛЬНОСТЬ И ЖЕЛАНИЕ ПОДЕЛИТЬСЯ С ДРУЗЬЯМИ:\n"
            "   - (+8 .. +10): Смешные курьёзы, невероятный абсурд, юмор («Индусы сушат дорогу вентиляторами», «Енот угнал машину»).\n"
            "   - (+1 .. +7): Позитивные, добрые или любопытные новости.\n"
            "   - (0): Сухой нейтральный официаз или ведомственный отчет.\n"
            "   - (-1 .. -5): Бытовые проблемы, тревожные новости, ограничения, рост цен.\n"
            "   - (-6 .. -10): Гнетущий негатив, стихийные бедствия, ураганы, наводнения, режим ЧС («Режим ЧС из-за урагана» = -8).\n\n"
            "Верни строго JSON-массив объектов следующей структуры:\n"
            "[\n"
            "  {\n"
            '    "id": "...",\n'
            '    "ru_headline": "Заголовок на русском",\n'
            '    "has_victims": false,\n'
            '    "relevance": 4,\n'
            '    "significance": 2,\n'
            '    "virality": 9\n'
            "  }\n"
            "]\n\n"
            f"Вот список новостей для оценки:\n{payload_json}"
        )

        import time
        models_to_try = ["gemini-2.0-flash", "gemini-2.5-flash"]
        for model in models_to_try:
            for retry in range(3):
                try:
                    endpoint = (
                        "https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{model}:generateContent?key={self.api_key}"
                    )
                    response = httpx.post(
                        endpoint,
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"response_mime_type": "application/json"},
                        },
                        timeout=45.0,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(raw_text)
                        if isinstance(parsed, list):
                            for res in parsed:
                                # Standardize virality / comedic mapping for backwards compatibility
                                v = res.get("virality")
                                if v is None:
                                    c = res.get("comedic_potential", 2)
                                    t = res.get("tone", 0)
                                    v = (c * 2) if t >= 0 else -c
                                res["virality"] = int(v)
                                res["comedic_potential"] = max(1, min(5, int(v))) if v > 0 else 1
                                res["tone"] = 1 if v > 0 else (-1 if v < 0 else 0)
                            logger.info("gemini_batch_scoring_success", model=model, count=len(parsed))
                            return parsed
                    elif response.status_code == 429:
                        wait_time = 5.0 * (retry + 1)
                        logger.warning("gemini_rate_limit_429", model=model, retry=retry, wait=wait_time)
                        time.sleep(wait_time)
                        continue
                except Exception as e:
                    logger.warning("gemini_batch_scoring_attempt_failed", model=model, error=str(e))
                    time.sleep(3.0)

        logger.error("gemini_batch_scoring_failed_using_heuristic")
        return self._heuristic_batch_scoring(items)

    def _heuristic_batch_scoring(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fallback heuristic scoring if LLM is unavailable."""
        results = []
        for idx, item in enumerate(items, 1):
            item_id = str(item.get("id", idx))
            h = item.get("headline", item.get("headline_original", ""))

            # Check victims
            has_victims = any(k in h.lower() for k in VICTIMS_KEYWORDS)

            # Check disasters
            disaster_kw = ["ураган", "шторм", "наводнени", "режим чс", "затопл", "засух"]
            is_disaster = any(k in h.lower() for k in disaster_kw)

            # Check priority viral
            is_viral = any(k in h.lower() for k in PRIORITY_VIRAL_KEYWORDS) and not is_disaster

            rel = 4 if not is_english(h) else 2
            sig = 3 if is_disaster else 2

            if has_victims or is_disaster:
                virality = -8 if is_disaster else -10
            elif is_viral:
                virality = 9
            else:
                virality = 0

            results.append({
                "id": item_id,
                "ru_headline": h,
                "has_victims": has_victims,
                "relevance": rel,
                "significance": sig,
                "virality": virality,
                "comedic_potential": max(1, virality) if virality > 0 else 1,
                "tone": 1 if virality > 0 else (-1 if virality < 0 else 0),
            })
        return results

    def curate_and_translate_news(
        self,
        categorized_news: list[dict[str, Any]],
        top_k: int = 10,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Backwards-compatible legacy wrapper for curate_and_translate_news."""
        all_candidates: list[dict[str, Any]] = []
        for cat in categorized_news:
            cat_title = cat.get("title", "")
            for item in cat.get("items", []):
                all_candidates.append({
                    "id": item.get("id", len(all_candidates) + 1),
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "source_name": item.get("source_name", "новости"),
                    "url": item.get("url", "#"),
                    "category_title": cat_title,
                })

        scored_items = self.score_batch(all_candidates)
        scored_map = {str(s["id"]): s for s in scored_items}

        ranked_list = []
        for cand in all_candidates:
            s = scored_map.get(str(cand["id"]), {})
            if s.get("has_victims"):
                continue
            quality = (
                s.get("relevance", 3) +
                s.get("comedic_potential", 2) +
                s.get("significance", 2) +
                s.get("tone", 0)
            )
            cand["headline"] = s.get("ru_headline", cand["headline"])
            ranked_list.append((quality, cand))

        ranked_list.sort(key=lambda x: x[0], reverse=True)
        top_10 = [
            {
                "headline": c["headline"],
                "source_name": c["source_name"],
                "url": c["url"],
                "category_title": c["category_title"],
            }
            for _, c in ranked_list[:top_k]
        ]

        return top_10, categorized_news
