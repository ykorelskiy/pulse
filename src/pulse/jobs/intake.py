"""Continuous news intake, scoring, and health monitoring job."""

import asyncio
import hashlib
from datetime import datetime, timezone

from pulse.config import get_config
from pulse.db.repo import NewsRepo
from pulse.digest.llm import LLMCurator
from pulse.logging import configure_logging, get_logger
from pulse.monitoring.health import SystemWatchdog
from pulse.sources.registry import SourceRegistry

logger = get_logger("pulse.jobs.intake")


def compute_headline_hash(headline: str) -> str:
    norm = " ".join(headline.lower().strip().split())
    return hashlib.md5(norm.encode("utf-8")).hexdigest()


async def run_intake_job() -> int:
    """Run intake for enabled RSS/Telegram feeds, score pending items, and check watchdog health.

    Returns:
        int: Total new articles collected and saved.
    """
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger.info("starting_intake_job")

    repo = NewsRepo()
    registry = SourceRegistry.load_from_config()
    enabled_adapters = registry.get_all()

    total_saved = 0

    # 1. Fetch articles from enabled adapters
    for adapter in enabled_adapters:
        try:
            articles = await adapter.fetch_latest()
            for art in articles:
                headline = getattr(art, "headline", getattr(art, "title", ""))
                if not headline:
                    continue

                h_hash = compute_headline_hash(headline)
                saved = repo.add_article(
                    source_id=adapter.source_id,
                    headline=headline,
                    url=art.url,
                    summary=getattr(art, "summary", "") or "",
                )
                if saved:
                    total_saved += 1
        except Exception as e:
            logger.error("adapter_fetch_failed", source=adapter.source_id, error=str(e))

    logger.info("intake_fetch_completed", total_saved=total_saved)

    # 2. Score pending news items using Gemini LLM Curator
    curator = LLMCurator()
    pending = repo.get_pending_news(limit=25)
    scored_count = 0
    if pending:
        logger.info("scoring_pending_news", count=len(pending))
        for item in pending:
            try:
                sc_res = await curator.score_news_item(item)
                if sc_res:
                    status = "rejected_victims" if sc_res.get("has_victims") else "scored"
                    update_data = {**sc_res, "status": status}
                    repo.update_scored_article(item["id"], update_data)
                    scored_count += 1
            except Exception as e:
                logger.error("news_item_scoring_failed", item_id=item.get("id"), error=str(e))

    logger.info("intake_scoring_completed", scored_count=scored_count)

    # 3. Execute System Watchdog checks
    try:
        watchdog = SystemWatchdog(silence_hours=3, cooldown_minutes=15)
        await watchdog.run_health_checks()
    except Exception as e:
        logger.error("watchdog_checks_failed", error=str(e))

    return total_saved


if __name__ == "__main__":
    asyncio.run(run_intake_job())
