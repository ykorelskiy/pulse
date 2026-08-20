"""Reminder job: cascading alerts before 20:00 MSK auto-publish."""

import argparse
import asyncio

from aiogram import Bot, types
from aiogram.enums import ParseMode

from pulse.config import get_config
from pulse.db.client import get_supabase_client
from pulse.logging import configure_logging, get_logger
from pulse.publisher.site_publisher import get_msk_today, has_valid_cover


URGENCY_CONFIG = {
    30: {"emoji": "⚠️", "label": "30 минут"},
    15: {"emoji": "🔶", "label": "15 минут"},
    5:  {"emoji": "🚨", "label": "5 минут"},
}


async def run_remind_publish(minutes_left: int = 30) -> None:
    """Send reminder to admin about missing cover or missing confirmation.

    Args:
        minutes_left: Minutes remaining until auto-publish (20:00 MSK).
    """
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger = get_logger("pulse.jobs.remind_publish")

    today_str = get_msk_today()
    logger.info("remind_publish_checking", date=today_str, minutes_left=minutes_left)

    client = get_supabase_client()
    res = client.table("site_issues").select("*").eq("issue_date", today_str).execute()
    rows = res.data or []

    if not rows:
        logger.info("no_issue_found_nothing_to_remind", date=today_str)
        return

    row = rows[0]
    image_path = row.get("image_path")
    confirmed = row.get("confirmed", False)
    has_cover = has_valid_cover(image_path)

    # If issue already published — no reminder needed
    if row.get("status") == "published":
        logger.info("already_published_no_reminder_needed", date=today_str)
        return

    # If cover uploaded AND confirmed — all good, no reminder
    if has_cover and confirmed:
        logger.info("cover_and_confirmed_no_reminder_needed", date=today_str)
        return

    # Something is missing — build alert
    target_chat_id = cfg.ADMIN_CHAT_ID
    if not target_chat_id or str(target_chat_id) == "123456789":
        logger.warning("admin_chat_id_not_set_skipping_reminder")
        return

    urgency = URGENCY_CONFIG.get(minutes_left, {"emoji": "⚠️", "label": f"{minutes_left} мин"})
    emoji = urgency["emoji"]
    time_label = urgency["label"]

    # Determine what's missing
    if not has_cover:
        problem = "🖼 Обложка НЕ загружена!"
        action = "Отправьте фото обложки боту прямо сейчас."
    else:
        problem = "☑️ Публикация НЕ подтверждена!"
        action = "Нажмите кнопку «Подтвердить» ниже."

    text = (
        f"{emoji} **До автопубликации осталось {time_label}!**\n\n"
        f"Выпуск «Пульс дня — {today_str}»:\n"
        f"{problem}\n\n"
        f"{action}\n\n"
        f"Автопубликация запланирована на **20:00 МСК**."
    )

    # Build keyboard with confirm button (if cover exists but not confirmed)
    reply_markup = None
    if has_cover and not confirmed:
        reply_markup = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="✅ Подтвердить публикацию в 20:00",
                    callback_data=f"confirm_publish_{today_str}",
                )
            ]]
        )

    bot = Bot(token=cfg.TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=target_chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
        logger.info("reminder_sent_to_admin", date=today_str, minutes_left=minutes_left,
                     has_cover=has_cover, confirmed=confirmed)
    except Exception as e:
        logger.error("failed_sending_reminder", error=str(e))
    finally:
        await bot.session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes-left", type=int, default=30,
                        help="Minutes remaining until auto-publish")
    args = parser.parse_args()
    asyncio.run(run_remind_publish(minutes_left=args.minutes_left))
