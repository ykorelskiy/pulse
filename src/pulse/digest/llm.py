"""Two-phase LLM Curator: Groq (primary) → Gemini (fallback) → Heuristic.

Phase 1: Sentiment + translation (ALL items)  → filters out negative
Phase 2: Virality scoring (ONLY positive/neutral items) → saves tokens
"""

import hashlib
import json
import re
import time
from typing import Any

import httpx

from pulse.config import get_config
from pulse.logging import get_logger

logger = get_logger("pulse.digest.llm")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

GEMINI_MODELS = ["gemini-2.0-flash", "gemini-2.5-flash"]

CHUNK_SIZE = 30  # Groq handles 30 items easily

VICTIMS_KEYWORDS = [
    "погиб", "пострад", "убит", "гибель", "ранен", "жертв", "убийств",
    "крушени", "авари", "рухнул", "катастроф", "пожар",
    "утону", "утоп", "мёртв", "мертв", "мина", "мине", "подорв",
    "похищ", "схватил", "смерт", "труп", "рака", "онкол", "сожрал", "трагед",
]


def is_english(text: str) -> bool:
    """Check if string contains mostly English characters."""
    ascii_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return ascii_count > len(text) * 0.3


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

PHASE1_SYSTEM = """Для каждой новости определи:
1. sentiment: positive, negative или neutral
2. ru_title: краткий заголовок на русском (если на английском — переведи)

Верни строго JSON-массив: [{"id":"...","sentiment":"...","ru_title":"..."}]
Не добавляй пояснений."""

PHASE2_SYSTEM = """Оцени каждую новость по 3 критериям:
1. virality (-10..+10): желание поделиться с друзьями (+8..+10 = курьёзы/абсурд/юмор, 0 = сухой официоз, -1..-10 = тревога/негатив)
2. relevance (1-5): интересность для массового читателя из РФ и СНГ
3. significance (1-5): глобальный масштаб события

Верни строго JSON-массив: [{"id":"...","virality":...,"relevance":...,"significance":...}]
Не добавляй пояснений."""


# ---------------------------------------------------------------------------
# LLMCurator
# ---------------------------------------------------------------------------

class LLMCurator:
    """Two-phase LLM scoring: sentiment first, then virality for non-negative."""

    def __init__(self, api_key: str | None = None) -> None:
        cfg = get_config().settings
        self.gemini_key = api_key or cfg.GEMINI_API_KEY
        self.groq_key = cfg.GROQ_API_KEY

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def score_batch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Score items in two phases: sentiment → virality.

        Returns list of dicts with keys:
            id, ru_headline, has_victims, relevance, significance,
            virality, comedic_potential, tone
        """
        if not items:
            return []

        # === PHASE 1: Sentiment + translation (ALL items) ===
        phase1 = self._phase1_sentiment(items)
        phase1_map = {str(r.get("id", "")): r for r in phase1}

        results: list[dict[str, Any]] = []
        positive_neutral_items: list[dict[str, Any]] = []

        for item in items:
            item_id = str(item.get("id", ""))
            p1 = phase1_map.get(item_id, {})
            sentiment = p1.get("sentiment", "neutral")
            ru_title = p1.get("ru_title", item.get("headline", ""))

            if sentiment == "negative":
                # Immediately reject — no Phase 2 needed
                results.append({
                    "id": item_id,
                    "ru_headline": ru_title,
                    "has_victims": True,
                    "relevance": 0,
                    "significance": 0,
                    "virality": 0,
                    "comedic_potential": 1,
                    "tone": -1,
                })
            else:
                # Prepare for Phase 2
                positive_neutral_items.append({
                    "id": item_id,
                    "headline": ru_title,
                    "sentiment": sentiment,
                    "_original_item": item,
                })

        # === PHASE 2: Virality scoring (ONLY positive/neutral) ===
        if positive_neutral_items:
            phase2 = self._phase2_virality(positive_neutral_items)
            phase2_map = {str(r.get("id", "")): r for r in phase2}

            for pn_item in positive_neutral_items:
                item_id = pn_item["id"]
                p2 = phase2_map.get(item_id, {})
                v = int(p2.get("virality", 0))
                rel = int(p2.get("relevance", 3))
                sig = int(p2.get("significance", 2))

                results.append({
                    "id": item_id,
                    "ru_headline": pn_item["headline"],
                    "has_victims": False,
                    "relevance": max(1, min(5, rel)),
                    "significance": max(1, min(5, sig)),
                    "virality": max(-10, min(10, v)),
                    "comedic_potential": max(1, min(5, abs(v))) if v > 0 else 1,
                    "tone": 1 if v > 0 else (-1 if v < 0 else 0),
                })

        neg_count = sum(1 for r in results if r.get("has_victims"))
        pos_count = len(results) - neg_count
        logger.info("two_phase_scoring_complete",
                     total=len(results), negative=neg_count, positive_neutral=pos_count)
        return results

    # -----------------------------------------------------------------------
    # Phase 1: Sentiment + Translation
    # -----------------------------------------------------------------------

    def _phase1_sentiment(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Classify sentiment and translate headlines for all items."""
        all_results: list[dict[str, Any]] = []
        for i in range(0, len(items), CHUNK_SIZE):
            chunk = items[i:i + CHUNK_SIZE]
            payload = "\n".join(
                f'{str(item.get("id", idx))}. {item.get("headline", "")}'
                for idx, item in enumerate(chunk, 1)
            )
            # Log the IDs we're sending for debugging
            chunk_ids = [str(item.get("id", idx)) for idx, item in enumerate(chunk, 1)]
            logger.info("phase1_chunk", chunk_idx=i // CHUNK_SIZE, ids_count=len(chunk_ids))
            user_msg = f"Новости:\n{payload}"

            parsed = self._call_llm(PHASE1_SYSTEM, user_msg, phase="phase1_sentiment")
            if parsed:
                all_results.extend(parsed)
            else:
                # Heuristic fallback for Phase 1
                all_results.extend(self._heuristic_sentiment(chunk))

            if i + CHUNK_SIZE < len(items):
                time.sleep(1.0)

        return all_results

    # -----------------------------------------------------------------------
    # Phase 2: Virality + Relevance + Significance
    # -----------------------------------------------------------------------

    def _phase2_virality(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Score virality/relevance/significance for positive/neutral items only."""
        all_results: list[dict[str, Any]] = []
        for i in range(0, len(items), CHUNK_SIZE):
            chunk = items[i:i + CHUNK_SIZE]
            payload = "\n".join(
                f'{item["id"]}. {item["headline"]}'
                for item in chunk
            )
            user_msg = f"Новости:\n{payload}"

            parsed = self._call_llm(PHASE2_SYSTEM, user_msg, phase="phase2_virality")
            if parsed:
                all_results.extend(parsed)
            else:
                # Heuristic fallback for Phase 2
                all_results.extend(self._heuristic_virality(chunk))

            if i + CHUNK_SIZE < len(items):
                time.sleep(1.0)

        return all_results

    # -----------------------------------------------------------------------
    # LLM Call: Groq → Gemini → None
    # -----------------------------------------------------------------------

    def _call_llm(
        self,
        system_prompt: str,
        user_msg: str,
        phase: str = "",
    ) -> list[dict[str, Any]] | None:
        """Try Groq first, then Gemini, return parsed JSON list or None."""

        # --- Try Groq ---
        if self.groq_key:
            result = self._call_groq(system_prompt, user_msg, phase)
            if result is not None:
                return result

        # --- Try Gemini ---
        if self.gemini_key:
            result = self._call_gemini(system_prompt, user_msg, phase)
            if result is not None:
                return result

        return None

    def _call_groq(
        self,
        system_prompt: str,
        user_msg: str,
        phase: str = "",
    ) -> list[dict[str, Any]] | None:
        """Call Groq API (OpenAI-compatible)."""
        for retry in range(3):
            try:
                response = httpx.post(
                    GROQ_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self.groq_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 4000,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    raw = data["choices"][0]["message"]["content"]
                    parsed = self._parse_json_response(raw)
                    if parsed:
                        usage = data.get("usage", {})
                        logger.info("groq_success",
                                    phase=phase,
                                    model=GROQ_MODEL,
                                    count=len(parsed),
                                    tokens=usage.get("total_tokens", 0))
                        return parsed
                elif response.status_code == 429:
                    wait = 5.0 * (retry + 1)
                    logger.warning("groq_rate_limit_429", phase=phase, retry=retry, wait=wait)
                    time.sleep(wait)
                    continue
                else:
                    logger.warning("groq_error", phase=phase, status=response.status_code,
                                   body=response.text[:200])
            except Exception as e:
                logger.warning("groq_exception", phase=phase, error=str(e))
                time.sleep(2.0)

        logger.warning("groq_exhausted_falling_back_to_gemini", phase=phase)
        return None

    def _call_gemini(
        self,
        system_prompt: str,
        user_msg: str,
        phase: str = "",
    ) -> list[dict[str, Any]] | None:
        """Call Gemini API as fallback."""
        prompt = f"{system_prompt}\n\n{user_msg}"
        for model in GEMINI_MODELS:
            for retry in range(3):
                try:
                    endpoint = (
                        "https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{model}:generateContent?key={self.gemini_key}"
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
                        raw = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = self._parse_json_response(raw)
                        if parsed:
                            logger.info("gemini_fallback_success",
                                        phase=phase, model=model, count=len(parsed))
                            return parsed
                    elif response.status_code == 429:
                        wait = 5.0 * (retry + 1)
                        logger.warning("gemini_rate_limit_429",
                                       phase=phase, model=model, retry=retry, wait=wait)
                        time.sleep(wait)
                        continue
                except Exception as e:
                    logger.warning("gemini_exception", phase=phase, model=model, error=str(e))
                    time.sleep(3.0)

        logger.error("gemini_fallback_exhausted", phase=phase)
        return None

    # -----------------------------------------------------------------------
    # JSON parsing helper
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(raw: str) -> list[dict[str, Any]] | None:
        """Parse JSON response, handle both array and object wrappers."""
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                # Groq sometimes wraps in {"news": [...]} or {"results": [...]}
                for key in ("news", "results", "items", "data", "evaluations", "scores"):
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                # Fallback: if there's any value that is a list, assume it's the items array
                for val in parsed.values():
                    if isinstance(val, list):
                        return val
                return [parsed]
            return None
        except json.JSONDecodeError:
            # Try to extract JSON array from markdown code blocks
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return None

    # -----------------------------------------------------------------------
    # Heuristic fallbacks
    # -----------------------------------------------------------------------

    def _heuristic_sentiment(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fallback sentiment classification using keyword matching."""
        logger.warning("using_heuristic_sentiment", count=len(items))
        results = []
        for item in items:
            item_id = str(item.get("id", ""))
            h = item.get("headline", "")
            has_victims = any(k in h.lower() for k in VICTIMS_KEYWORDS)
            sentiment = "negative" if has_victims else "neutral"
            results.append({
                "id": item_id,
                "sentiment": sentiment,
                "ru_title": h,
            })
        return results

    def _heuristic_virality(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fallback virality scoring using hash-based variation."""
        logger.warning("using_heuristic_virality", count=len(items))
        results = []
        for item in items:
            item_id = str(item.get("id", ""))
            h = item.get("headline", "")
            h_val = int(hashlib.md5(h.encode("utf-8")).hexdigest(), 16)
            results.append({
                "id": item_id,
                "virality": ((h_val >> 9) % 7) - 2,
                "relevance": (3 if not is_english(h) else 2) + (h_val % 3),
                "significance": 1 + ((h_val >> 3) % 3),
            })
        return results

    # -----------------------------------------------------------------------
    # Legacy compatibility wrapper
    # -----------------------------------------------------------------------

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
