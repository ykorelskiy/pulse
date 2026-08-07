"""Hourly news collection background job."""

import asyncio

from pulse.config import get_config
from pulse.db.repo import NewsRepo
from pulse.logging import configure_logging, get_logger
from pulse.sources.registry import SourceRegistry


async def run_collect_job() -> int:
    """Collect latest news headlines from active RSS feeds and save to Supabase.

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
                    )
                    new_count += 1
                except Exception as ex:
                    logger.debug("skip_article", url=article.url, reason=str(ex))
        except Exception as e:
            logger.error("feed_fetch_failed", source_id=adapter.source_id, error=str(e))


    logger.info("news_collection_completed", processed_count=new_count)
    return new_count


def main() -> None:
    asyncio.run(run_collect_job())


if __name__ == "__main__":
    main()
