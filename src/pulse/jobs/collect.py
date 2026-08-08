"""Hourly news collection & scoring background job."""

import asyncio
from typing import Any

from pulse.config import get_config
from pulse.db.repo import NewsRepo
from pulse.digest.cluster import NewsClusterer
from pulse.digest.llm import LLMCurator
from pulse.digest.translator import is_english, translate_to_russian
from pulse.logging import configure_logging, get_logger
from pulse.sources.registry import SourceRegistry


async def process_pending_scoring(repo: NewsRepo, curator: LLMCurator, clusterer: NewsClusterer, logger: Any) -> int:
    """Evaluate ALL pending news items in micro-batches and update Supabase."""
    total_scored = 0
    max_iterations = 100  # Safety limit to prevent infinite loops

    for iteration in range(max_iterations):
        pending_items = repo.get_pending_news(limit=200)
        if not pending_items:
            break

        logger.info("scoring_iteration", iteration=iteration, pending_count=len(pending_items))
        recent_24h = repo.get_scored_24h_news()

        # Process in micro-batches of 50 items (larger batches = fewer API calls)
        batch_size = 50
        for i in range(0, len(pending_items), batch_size):
            batch = pending_items[i:i + batch_size]
            scored_results = curator.score_batch(batch)
            scored_map = {str(s["id"]): s for s in scored_results}

            for item in batch:
                item_id = str(item.get("id"))
                eval_res = scored_map.get(item_id, {})

                has_victims = eval_res.get("has_victims", False)
                ru_headline = eval_res.get("ru_headline") or item.get("headline", "")
                if is_english(ru_headline):
                    ru_headline = translate_to_russian(ru_headline)

                if has_victims:
                    status = "rejected_victims"
                    cluster_id, _ = clusterer.find_or_create_cluster({"id": item_id, "ru_headline": ru_headline}, recent_24h)
                else:
                    cluster_id, is_archived = clusterer.find_or_create_cluster({"id": item_id, "ru_headline": ru_headline}, recent_24h)
                    status = "archived" if is_archived else "scored"

                virality = int(eval_res.get("virality", 0))
                comedic_potential = max(1, min(5, abs(virality))) if virality != 0 else 1
                tone = 1 if virality > 0 else (-1 if virality < 0 else 0)

                update_data = {
                    "ru_headline": ru_headline,
                    "has_victims": has_victims,
                    "relevance": eval_res.get("relevance", 3),
                    "comedic_potential": comedic_potential,
                    "significance": eval_res.get("significance", 2),
                    "tone": tone,
                    "cluster_id": cluster_id,
                    "status": status,
                }

                repo.update_scored_article(item_id, update_data)
                total_scored += 1

            await asyncio.sleep(5.0)

    logger.info("microbatch_scoring_completed", count=total_scored)
    return total_scored


async def run_collect_job() -> int:
    """Collect latest news headlines from active RSS feeds, score and cluster them.

    Returns:
        int: Number of new news items processed.
    """
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger = get_logger("pulse.jobs.collect")

    logger.info("starting_news_collection")
    registry = SourceRegistry.load_from_config()
    adapters = registry.get_all()

    repo = NewsRepo()
    curator = LLMCurator()
    clusterer = NewsClusterer()
    new_count = 0

    for adapter in adapters:
        try:
            repo.add_source(
                source_id=adapter.source_id,
                name=adapter.name,
                url=adapter.url,
                category=adapter.category,
            )
            logger.info("fetching_feed", source_id=adapter.source_id)
            articles = await adapter.fetch_latest()
            for article in articles:
                pub_iso = article.published_at.isoformat() if article.published_at else None
                try:
                    repo.add_article(
                        source_id=article.source_id,
                        headline=article.headline,
                        url=article.url,
                        published_at=pub_iso,
                        summary=getattr(article, "summary", ""),
                    )
                    new_count += 1
                except Exception as ex:
                    logger.debug("skip_article", url=article.url, reason=str(ex))
        except Exception as e:
            logger.error("feed_fetch_failed", source_id=adapter.source_id, error=str(e))

    # Trigger micro-batch scoring & clustering immediately after collection
    try:
        await process_pending_scoring(repo, curator, clusterer, logger)
    except Exception as ex:
        logger.error("microbatch_scoring_error", error=str(ex))

    logger.info("news_collection_completed", processed_count=new_count)
    return new_count


def main() -> None:
    asyncio.run(run_collect_job())


if __name__ == "__main__":
    main()
