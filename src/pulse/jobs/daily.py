"""Daily author brief construction job."""

import asyncio
from datetime import datetime, timezone

from aiogram import Bot

from pulse.briefsmith.builder import BriefBuilder
from pulse.briefsmith.policy import EditorialPolicyEnforcer
from pulse.config import get_config
from pulse.db.repo import BriefsRepo, IssuesRepo
from pulse.digest.ranker import TopicRanker
from pulse.logging import configure_logging, get_logger


async def run_daily_job() -> str:
    """Build daily author brief and send to admin Telegram chat (@anta9onist).

    Returns:
        str: Generated brief text.
    """
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger = get_logger("pulse.jobs.daily")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info("starting_daily_brief_job", date=today_str)

    ranker = TopicRanker()
    categorized_news = ranker.get_categorized_news(items_per_category=5)
    raw_words = ranker.get_top_reader_words(limit=5)

    policy = EditorialPolicyEnforcer()
    _, words = policy.sanitize_input([], raw_words)

    builder = BriefBuilder()
    brief_text = builder.build_daily_brief(
        date_str=today_str,
        categorized_news=categorized_news,
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
            top_news=categorized_news,
        )



    # Send brief to admin chat
    bot = Bot(token=cfg.TELEGRAM_BOT_TOKEN)
    try:
        logger.info("sending_brief_to_admin", admin_chat_id=cfg.ADMIN_CHAT_ID)
        if len(brief_text) <= 4000:
            await bot.send_message(
                chat_id=cfg.ADMIN_CHAT_ID,
                text=brief_text,
                parse_mode="Markdown",
            )
        else:
            parts = brief_text.split("\n\n")
            current_chunk = ""
            for part in parts:
                if len(current_chunk) + len(part) + 2 <= 4000:
                    current_chunk = f"{current_chunk}\n\n{part}".strip()
                else:
                    if current_chunk:
                        await bot.send_message(
                            chat_id=cfg.ADMIN_CHAT_ID,
                            text=current_chunk,
                            parse_mode="Markdown",
                        )
                    current_chunk = part
            if current_chunk:
                await bot.send_message(
                    chat_id=cfg.ADMIN_CHAT_ID,
                    text=current_chunk,
                    parse_mode="Markdown",
                )
    except Exception as e:
        logger.error("failed_sending_brief_to_admin", error=str(e))
    finally:
        await bot.session.close()


    logger.info("daily_brief_job_completed", date=today_str)
    return brief_text


def main() -> None:
    asyncio.run(run_daily_job())


if __name__ == "__main__":
    main()
