"""Topic ranker for categorizing, scoring, and source statistics."""

import contextlib
from collections import Counter
from typing import Any

from pulse.config import CATEGORIES_INFO, CATEGORY_FALLBACKS
from pulse.db.repo import NewsRepo, WordsRepo
from pulse.digest.llm import LLMCurator
from pulse.sources.registry import SourceRegistry


def extract_key_phrase(headline: str) -> str:
    """Extract first 5 words or clean key phrase from headline."""
    if not headline:
        return ""
    words = headline.strip().split()
    return " ".join(words[:5])


class TopicRanker:

    """Ranks and categorizes collected news, generating source statistics."""

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
        items_per_category: int = 10,
        top_k: int = 10,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Neural curation returning TOP-10, TOP-50 flat list, and source statistics.

        Returns:
            tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
                - Top 10 neural-selected news headlines with source and url
                - Top 50 candidate news headlines flat list
                - Source audit statistics (analyzed, in_top_50, in_top_10)
        """
        categorized_raw, source_stats_map, flat_top_50 = self.get_categorized_news_and_stats(
            items_per_category=items_per_category,
            top_50_limit=50,
        )

        top_10, _ = self.curator.curate_and_translate_news(categorized_raw, top_k=top_k)

        # Update in_top_10 count in source_stats_map
        for item in top_10:
            src_name = item.get("source_name", "")
            if src_name in source_stats_map:
                source_stats_map[src_name]["in_top_10"] += 1


        source_stats_list = list(source_stats_map.values())
        source_stats_list.sort(key=lambda x: x["analyzed"], reverse=True)

        return top_10, flat_top_50, source_stats_list

    def get_categorized_news_and_stats(
        self,
        items_per_category: int = 10,
        top_50_limit: int = 50,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """Extract categorized news, build top 50 flat list and source statistics."""
        source_map: dict[str, dict[str, str]] = {}
        source_stats_map: dict[str, dict[str, Any]] = {}

        with contextlib.suppress(Exception):
            registry = SourceRegistry.load_from_config()
            for adapter in registry.get_all():
                sname = getattr(adapter, "name", adapter.source_id)
                source_map[adapter.source_id] = {
                    "category": getattr(adapter, "category", "ru_news"),
                    "name": sname,
                }
                source_stats_map[sname] = {
                    "name": sname,
                    "analyzed": 0,
                    "in_top_50": 0,
                    "in_top_10": 0,
                }

        collected_articles: list[dict[str, Any]] = []
        with contextlib.suppress(Exception):
            collected_articles = self.news_repo.get_latest_news(limit=500)

        categorized_buckets: dict[str, list[dict[str, str]]] = {
            cat["code"]: [] for cat in CATEGORIES_INFO
        }
        seen_headlines: set[str] = set()
        flat_top_50: list[dict[str, Any]] = []

        for art in collected_articles:
            headline = art.get("headline", "").strip() if art.get("headline") else ""
            url = art.get("url", "#")
            summary = (art.get("summary") or "").strip()
            source_id = art.get("source_id", "")

            if not headline:
                continue

            src_info = source_map.get(source_id, {"category": "ru_news", "name": source_id})
            sname = src_info["name"]

            if sname not in source_stats_map:
                source_stats_map[sname] = {
                    "name": sname,
                    "analyzed": 0,
                    "in_top_50": 0,
                    "in_top_10": 0,
                }
            source_stats_map[sname]["analyzed"] += 1

            if headline.lower() in seen_headlines:
                continue

            seen_headlines.add(headline.lower())

            item_dict = {
                "headline": headline,
                "summary": summary,
                "source_name": sname,
                "url": url,
            }

            if len(flat_top_50) < top_50_limit:
                flat_top_50.append(item_dict)
                source_stats_map[sname]["in_top_50"] += 1

            cat_code = src_info["category"]
            if cat_code not in categorized_buckets:
                cat_code = "ru_news"

            if len(categorized_buckets[cat_code]) < items_per_category:
                categorized_buckets[cat_code].append(item_dict)

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

        return result, source_stats_map, flat_top_50

    def get_categorized_news(self, items_per_category: int = 10) -> list[dict[str, Any]]:
        """Legacy helper for backward compatibility."""
        result, _, _ = self.get_categorized_news_and_stats(items_per_category=items_per_category)
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
