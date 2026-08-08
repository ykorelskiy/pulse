"""Daily author brief construction job."""

import asyncio
from datetime import datetime, timezone

from aiogram import Bot, types
from aiogram.enums import ParseMode

from pulse.briefsmith.builder import BriefBuilder
from pulse.briefsmith.policy import EditorialPolicyEnforcer
from pulse.config import get_config
from pulse.db.repo import BriefsRepo, IssuesRepo
from pulse.digest.ranker import TopicRanker
from pulse.logging import configure_logging, get_logger
from pulse.publisher.caption import CaptionBuilder
from pulse.publisher.site_publisher import get_msk_today


async def run_daily_job() -> str:
    """Build daily curated 15-news text digest and send to author Telegram chat.

    Returns:
        str: Generated news text digest.
    """
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger = get_logger("pulse.jobs.daily")

    today_str = get_msk_today()
    logger.info("starting_daily_digest_job", date=today_str)

    ranker = TopicRanker()
    top_10, top_50, source_stats = ranker.get_top_curated_digest(items_per_category=10, top_k=10)
    raw_words = ranker.get_top_reader_words(limit=5)

    policy = EditorialPolicyEnforcer()
    _, words = policy.sanitize_input([], raw_words)

    # Save internal brief to DB history for debugging
    builder = BriefBuilder()
    brief_text = builder.build_daily_brief(
        date_str=today_str,
        top_10_curated=top_10,
        top_50_flat=top_50,
        source_stats=source_stats,
        top_words=words,
        previous_winner_text=None,
    )

    issues_repo = IssuesRepo()
    issue = None
    try:
        issue = issues_repo.create_for_date(
            issue_date=today_str,
            brief_used=brief_text,
            status="awaiting_image",
        )
    except Exception:
        logger.info("issue_already_exists_for_date", date=today_str)
        issue = issues_repo.get_by_date(today_str)

    if issue and isinstance(issue, dict) and "id" in issue:
        briefs_repo = BriefsRepo()
        briefs_repo.save_brief(
            issue_id=issue["id"],
            brief_text=brief_text,
            top_words=words,
            top_news=top_50,
        )

    # Format the 15 news text digest for author's poster generation
    caption_builder = CaptionBuilder()
    formatted_post_text = caption_builder.build_caption(
        date_str=today_str,
        news_items=top_50[:15],
    )

    # Send formatted text message to admin Telegram chat
    target_chat_id = cfg.ADMIN_CHAT_ID
    if not target_chat_id or str(target_chat_id) == "123456789":
        logger.warning("admin_chat_id_not_set", chat_id=target_chat_id)
        return formatted_post_text

    no_preview = types.LinkPreviewOptions(is_disabled=True)
    bot = Bot(token=cfg.TELEGRAM_BOT_TOKEN)
    try:
        logger.info("sending_daily_news_digest_to_admin", admin_chat_id=target_chat_id)

        header = f"📰 **ПОДБОРКА 15 НОВОСТЕЙ НА {today_str} (для рисования плаката):**\n\n"
        full_text = header + formatted_post_text

        lines = full_text.split("\n")
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) + 1 <= 3000:
                current_chunk = f"{current_chunk}\n{line}".strip() if current_chunk else line
            else:
                if current_chunk:
                    try:
                        await bot.send_message(
                            chat_id=target_chat_id,
                            text=current_chunk,
                            parse_mode=ParseMode.MARKDOWN,
                            link_preview_options=no_preview,
                        )
                    except Exception:
                        await bot.send_message(
                            chat_id=target_chat_id,
                            text=current_chunk,
                            parse_mode=None,
                            link_preview_options=no_preview,
                        )
                    await asyncio.sleep(0.3)
                current_chunk = line

        if current_chunk:
            try:
                await bot.send_message(
                    chat_id=target_chat_id,
                    text=current_chunk,
                    parse_mode=ParseMode.MARKDOWN,
                    link_preview_options=no_preview,
                )
            except Exception:
                await bot.send_message(
                    chat_id=target_chat_id,
                    text=current_chunk,
                    parse_mode=None,
                    link_preview_options=no_preview,
                )

        logger.info("daily_news_digest_sent_successfully", date=today_str)
    except Exception as e:
        logger.error("failed_sending_daily_news_digest_to_admin", error=str(e))
    finally:
        await bot.session.close()

    return formatted_post_text


if __name__ == "__main__":
    asyncio.run(run_daily_job())
