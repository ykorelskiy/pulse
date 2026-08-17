"""Topic ranker implementing deterministic SQL window ranking & cluster selection (TZ v2)."""

import contextlib
from datetime import datetime, timezone
from typing import Any

from pulse.config import CATEGORIES_INFO
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
    """Ranks collected news deterministically using TZ v2 scoring parameters."""

    def __init__(
        self,
        news_repo: NewsRepo | None = None,
        words_repo: WordsRepo | None = None,
        curator: LLMCurator | None = None,
        target_date_str: str | None = None,
    ) -> None:
        self.news_repo = news_repo or NewsRepo()
        self.words_repo = words_repo or WordsRepo()
        self.curator = curator or LLMCurator()
        self.target_date_str = target_date_str

    def get_top_curated_digest(
        self,
        items_per_category: int = 10,
        top_k: int = 10,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Deterministic ranking returning TOP-10, TOP-50 flat list, and source statistics.

        Returns:
            tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
                - Top 10 neural-scored and SQL-ranked news items
                - Top 50 candidate news headlines flat list
                - Source audit statistics (analyzed, in_top_50, in_top_10)
        """
        source_map: dict[str, str] = {}
        source_stats_map: dict[str, dict[str, Any]] = {}

        with contextlib.suppress(Exception):
            registry = SourceRegistry.load_from_config()
            for adapter in registry.get_all():
                sname = getattr(adapter, "name", adapter.source_id)
                source_map[adapter.source_id] = sname
                source_stats_map[sname] = {
                    "name": sname,
                    "analyzed": 0,
                    "in_top_50": 0,
                    "in_top_10": 0,
                }

        # Audit stats: count items ONLY from active enabled sources
        all_24h_items = [i for i in self.news_repo.get_all_24h_news(self.target_date_str) if str(i.get("source_id")) in source_map]
        for item in all_24h_items:
            sid = str(item.get("source_id") or "news")
            sname = source_map.get(sid, sid)
            if sname in source_stats_map:
                source_stats_map[sname]["analyzed"] += 1

        # Ranking: strictly ONLY use scored items from active enabled sources (exclude pessimized/negative scored)
        raw_items = [
            i for i in self.news_repo.get_scored_24h_news(self.target_date_str)
            if str(i.get("source_id")) in source_map
            and i.get("status") == "scored"
            and i.get("status") not in ("excluded", "rejected")
            and float(i.get("total_score") or i.get("score") or 0.0) >= 0
        ]

        now = datetime.now(timezone.utc)

        # First pass: group by cluster to calculate breadth_score
        cluster_sources: dict[str, set[str]] = {}
        for item in raw_items:
            cid = str(item.get("cluster_id") or item.get("id"))
            sid = str(item.get("source_id") or "news")
            if cid not in cluster_sources:
                cluster_sources[cid] = set()
            cluster_sources[cid].add(sid)

        scored_items: list[tuple[float, dict[str, Any]]] = []
        seen_headlines: set[str] = set()

        for item in raw_items:
            sid = str(item.get("source_id") or "news")
            sname = source_map.get(sid, sid)

            headline = (item.get("ru_headline") or item.get("headline") or "").strip()
            if not headline or headline.lower() in seen_headlines:
                continue

            # Semantic emotional impact filter (evaluated by Gemini LLM)
            if item.get("has_victims") is True or item.get("status") == "rejected_victims":
                continue

            seen_headlines.add(headline.lower())

            # Calculate Scores
            rel = item.get("relevance") or 3
            sig = item.get("significance") or 2
            virality = item.get("virality")
            if virality is None:
                comedic = item.get("comedic_potential") or 2
                tone = item.get("tone") or 0
                if tone < 0:
                    virality = -abs(comedic) * 2
                elif tone > 0:
                    virality = abs(comedic) * 2
                else:
                    virality = 0
            quality_score = rel + sig + int(virality)

            cid = str(item.get("cluster_id") or item.get("id"))
            breadth_score = min(len(cluster_sources.get(cid, {sid})), 5)

            # Freshness score: DISABLED FOR EXPERIMENT (until Aug 12, 2026)
            # Was: freshness_score = max(0, 6 - int(hours_old / 4.0))
            freshness_score = 0

            # Total = Quality score only (Freshness disabled)
            total_score = quality_score
            item_copy = dict(item)
            item_copy["headline"] = headline
            item_copy["source_name"] = sname
            item_copy["total_score"] = total_score
            item_copy["cluster_id"] = cid

            scored_items.append((total_score, item_copy))

        # Sort by total_score desc
        scored_items.sort(key=lambda x: x[0], reverse=True)

        # Deduplicate clusters (1 best item per cluster_id)
        cluster_seen: set[str] = set()
        deduped_items: list[dict[str, Any]] = []

        for score, item in scored_items:
            cid = item["cluster_id"]
            if cid not in cluster_seen:
                cluster_seen.add(cid)
                deduped_items.append(item)

        # Top 10 selection with diversity cap (max 2 items per source)
        top_10_raw: list[dict[str, Any]] = []
        source_counts_top_10: dict[str, int] = {}

        for item in deduped_items:
            sname = item["source_name"]
            if source_counts_top_10.get(sname, 0) < 2:
                top_10_raw.append(item)
                source_counts_top_10[sname] = source_counts_top_10.get(sname, 0) + 1
            if len(top_10_raw) >= top_k:
                break

        top_10: list[dict[str, str]] = []
        for item in top_10_raw:
            top_10.append({
                "headline": item["headline"],
                "source_name": item["source_name"],
                "url": item.get("url", "#"),
                "total_score": item.get("total_score"),
                "category_title": "Главные новости дня",
            })
            sname = item["source_name"]
            if sname in source_stats_map:
                source_stats_map[sname]["in_top_10"] += 1

        # Top 50 flat list with diversity cap (max 4 items per source)
        flat_top_50: list[dict[str, Any]] = []
        source_counts_top_50: dict[str, int] = {}

        for item in deduped_items:
            sname = item["source_name"]
            if source_counts_top_50.get(sname, 0) < 4:
                flat_top_50.append(item)
                source_counts_top_50[sname] = source_counts_top_50.get(sname, 0) + 1
            if len(flat_top_50) >= 50:
                break
        for item in flat_top_50:
            sname = item["source_name"]
            if sname in source_stats_map:
                source_stats_map[sname]["in_top_50"] += 1

        source_stats_list = list(source_stats_map.values())
        source_stats_list.sort(key=lambda x: x["analyzed"], reverse=True)

        return top_10, flat_top_50, source_stats_list

    def get_categorized_news_and_stats(
        self,
        items_per_category: int = 10,
        top_50_limit: int = 50,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """Legacy helper compatibility."""
        top_10, flat_top_50, stats = self.get_top_curated_digest(
            items_per_category=items_per_category,
            top_k=top_50_limit,
        )
        stats_map = {s["name"]: s for s in stats}
        cats = [
            {
                "code": "ru_news",
                "title": "Главные события дня",
                "weight": "100%",
                "icon": "📰",
                "items": flat_top_50[:10],
            }
        ]
        return cats, stats_map, flat_top_50

    def get_top_news_details(self, limit: int = 5) -> list[dict[str, str]]:
        top_10, _, _ = self.get_top_curated_digest(top_k=limit)
        return [
            {
                "phrase": item["headline"],
                "headline": item["headline"],
                "url": item["url"],
                "source_id": item["source_name"],
            }
            for item in top_10[:limit]
        ]

    def get_top_news_phrases(self, limit: int = 5) -> list[str]:
        details = self.get_top_news_details(limit=limit)
        return [item["headline"] for item in details]

    def get_top_reader_words(self, limit: int = 5) -> list[str]:
        words_entries = self.words_repo.get_recent_words(limit=100)
        from collections import Counter
        counter: Counter[str] = Counter()
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

    def get_legacy_vs_new_comparison(self, limit: int = 15) -> list[dict[str, Any]]:
        """Return side-by-side comparison of items under New (primary) vs Legacy model.

        New Model: Enforces strict CoT sentiment + victims pre-filter.
        Legacy Model: Raw total score ranking without victims pre-filter.
        """
        all_scored = self.news_repo.get_scored_24h_news(self.target_date_str)
        
        # New model filtering
        _, new_top50, _ = self.get_top_curated_digest(top_k=50)
        
        # Legacy ranking (ignoring status rejected_victims / has_victims)
        legacy_items = []
        for i in all_scored:
            rel = i.get("relevance") or 3
            sig = i.get("significance") or 2
            v = i.get("virality") or 0
            score = rel + sig + int(v)
            item_copy = dict(i)
            item_copy["legacy_score"] = score
            legacy_items.append(item_copy)
        
        legacy_items.sort(key=lambda x: x["legacy_score"], reverse=True)
        legacy_rank_map = {str(item.get("id")): rank for rank, item in enumerate(legacy_items, 1)}

        comparison = []
        for rank_new, item in enumerate(new_top50[:limit], 1):
            iid = str(item.get("id"))
            rank_legacy = legacy_rank_map.get(iid, "N/A")
            comparison.append({
                "new_rank": rank_new,
                "legacy_rank": rank_legacy,
                "headline": item.get("headline", ""),
                "score": item.get("total_score", 0),
                "url": item.get("url", ""),
            })

        return comparison

