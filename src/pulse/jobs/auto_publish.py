"""Auto-publish job: runs at 20:00 MSK via cron, publishes today's issue to all channels."""

import asyncio
from typing import Any

from aiogram import Bot, types
from aiogram.enums import ParseMode

from pulse.config import get_config
from pulse.db.client import get_supabase_client
from pulse.logging import configure_logging, get_logger
from pulse.publisher.orchestrator import MultiPublisherOrchestrator
from pulse.publisher.site_publisher import get_msk_today


async def run_auto_publish() -> None:
    """Publish today's issue to all channels (TG, VK, Site) if cover image exists."""
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger = get_logger("pulse.jobs.auto_publish")

    today_str = get_msk_today()
    logger.info("auto_publish_starting", date=today_str)

    client = get_supabase_client()
    res = client.table("site_issues").select("*").eq("issue_date", today_str).execute()
    rows = res.data or []

    if not rows:
        logger.warning("no_issue_found_for_today", date=today_str)
        return

    row = rows[0]
    image_path = row.get("image_path")

    if not image_path:
        logger.info("no_cover_uploaded_skipping_publish", date=today_str)
        return

    # Check if issue was already published today
    if row.get("status") == "published":
        logger.info("issue_already_published_skipping_duplicate", date=today_str)
        return

    # Build image URL
    img_url = f"https://zyoznyeqvorhztrpgdjw.supabase.co/storage/v1/object/public/pulse-covers/{image_path}"
    news_items: list[dict[str, Any]] = row.get("news") or []
    title = row.get("title")

    logger.info("publishing_to_all_channels", date=today_str, news_count=len(news_items))

    orchestrator = MultiPublisherOrchestrator()
    pub_results = await orchestrator.publish_all(
        issue_date=today_str,
        img_url=img_url,
        news_items=news_items,
        title=title,
    )

    # Mark issue as published in DB
    try:
        from datetime import datetime, timezone
        client.table("site_issues").update({
            "published": True,
            "status": "published",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }).eq("issue_date", today_str).execute()
    except Exception as e:
        logger.error("failed_updating_published_status_in_db", error=str(e))

    # Send report to admin
    target_chat_id = cfg.ADMIN_CHAT_ID
    if not target_chat_id or str(target_chat_id) == "123456789":
        logger.warning("admin_chat_id_not_set_skipping_report")
        return

    report_lines = [
        f"🎉 **АВТОПУБЛИКАЦИЯ ВЫПУСКА ОТ {today_str} ЗАВЕРШЕНА!**",
        "",
    ]

    tg = pub_results.get("telegram", {})
    if tg.get("success"):
        report_lines.append(f"✅ **Telegram-канал:** [Перейти к посту]({tg['url']})")
    else:
        report_lines.append(f"❌ **Telegram-канал:** {tg.get('error')}")

    vk = pub_results.get("vk", {})
    if vk.get("success"):
        report_lines.append(f"✅ **ВКонтакте:** [Перейти к посту]({vk['url']})")
    else:
        report_lines.append(f"❌ **ВКонтакте:** {vk.get('error')}")

    site = pub_results.get("website", {})
    if site.get("success"):
        report_lines.append(f"✅ **Веб-сайт:** [Смотреть выпуск]({site['url']})")
    else:
        report_lines.append(f"❌ **Веб-сайт:** {site.get('error')}")

    bot = Bot(token=cfg.TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=target_chat_id,
            text="\n".join(report_lines),
            parse_mode=ParseMode.MARKDOWN,
            link_preview_options=types.LinkPreviewOptions(is_disabled=True),
        )
    except Exception as e:
        logger.error("failed_sending_publish_report", error=str(e))
    finally:
        await bot.session.close()

    logger.info("auto_publish_completed", date=today_str, results=pub_results)


if __name__ == "__main__":
    asyncio.run(run_auto_publish())
