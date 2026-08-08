"""Reminder job: runs at 19:30 MSK, reminds author if publication is not confirmed."""

import asyncio

from aiogram import Bot, types
from aiogram.enums import ParseMode

from pulse.config import get_config
from pulse.db.client import get_supabase_client
from pulse.logging import configure_logging, get_logger
from pulse.publisher.site_publisher import get_msk_today


async def run_remind_publish() -> None:
    """Send reminder to admin if today's issue has cover but is not confirmed."""
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger = get_logger("pulse.jobs.remind_publish")

    today_str = get_msk_today()
    logger.info("remind_publish_checking", date=today_str)

    client = get_supabase_client()
    res = client.table("site_issues").select("*").eq("issue_date", today_str).execute()
    rows = res.data or []

    if not rows:
        logger.info("no_issue_found_nothing_to_remind", date=today_str)
        return

    row = rows[0]
    image_path = row.get("image_path")
    confirmed = row.get("confirmed", False)

    if not image_path:
        logger.info("no_cover_uploaded_nothing_to_remind", date=today_str)
        return

    if confirmed:
        logger.info("already_confirmed_no_reminder_needed", date=today_str)
        return

    # Cover exists but not confirmed — send reminder
    target_chat_id = cfg.ADMIN_CHAT_ID
    if not target_chat_id or str(target_chat_id) == "123456789":
        logger.warning("admin_chat_id_not_set_skipping_reminder")
        return

    confirm_kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Подтвердить публикацию в 20:00",
                    callback_data=f"confirm_publish_{today_str}",
                )
            ]
        ]
    )

    bot = Bot(token=cfg.TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=target_chat_id,
            text=(
                f"⚠️ **ВНИМАНИЕ! Публикация «Пульс дня — {today_str}» не подтверждена!**\n\n"
                f"Обложка загружена, но вы ещё не нажали кнопку подтверждения.\n"
                f"Выпуск выйдет автоматически в **20:00 МСК** в любом случае.\n\n"
                f"Нажмите кнопку ниже, чтобы подтвердить."
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=confirm_kbd,
        )
        logger.info("reminder_sent_to_admin", date=today_str)
    except Exception as e:
        logger.error("failed_sending_reminder", error=str(e))
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_remind_publish())
