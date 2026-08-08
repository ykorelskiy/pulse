"""Continuous news intake, scoring, and health monitoring job."""

import asyncio
import hashlib
import sys
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


async def run_fetch_job() -> int:
    """Fetch articles from RSS/Telegram feeds and save as pending in Supabase."""
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger.info("starting_intake_fetch_job")

    repo = NewsRepo()
    registry = SourceRegistry.load_from_config()
    enabled_adapters = registry.get_all()

    total_saved = 0
    for adapter in enabled_adapters:
        try:
            articles = await adapter.fetch_latest()
            for art in articles:
                headline = getattr(art, "headline", getattr(art, "title", ""))
                if not headline:
                    continue

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
    return total_saved


async def run_score_job() -> int:
    """Score pending news items via Gemini LLM and execute watchdog health checks."""
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger.info("starting_intake_score_job")

    repo = NewsRepo()
    curator = LLMCurator()
    pending = repo.get_pending_news(limit=100)
    scored_count = 0

    if pending:
        logger.info("scoring_pending_news", count=len(pending))
        try:
            scored_results = curator.score_batch(pending)
            for sc_res in scored_results:
                item_id = sc_res.get("id")
                if item_id:
                    status = "rejected_victims" if sc_res.get("has_victims") else "scored"
                    update_data = {**sc_res, "status": status}
                    repo.update_scored_article(item_id, update_data)
                    scored_count += 1
        except Exception as e:
            logger.error("batch_scoring_failed", error=str(e))

    logger.info("intake_scoring_completed", scored_count=scored_count)

    # Execute System Watchdog checks
    try:
        watchdog = SystemWatchdog(silence_hours=3, cooldown_minutes=15)
        await watchdog.run_health_checks()
    except Exception as e:
        logger.error("watchdog_checks_failed", error=str(e))

    return scored_count


async def run_intake_job(mode: str = "all") -> int:
    if mode == "fetch":
        return await run_fetch_job()
    elif mode == "score":
        return await run_score_job()
    else:
        f_count = await run_fetch_job()
        s_count = await run_score_job()
        return f_count + s_count


if __name__ == "__main__":
    mode_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    asyncio.run(run_intake_job(mode=mode_arg))
