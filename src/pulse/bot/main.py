"""Telegram Bot main entrypoint."""

import asyncio

from aiogram import Bot, Dispatcher

from pulse.bot.handlers import admin, word
from pulse.bot.middlewares import RateLimitMiddleware
from pulse.config import get_config
from pulse.logging import configure_logging, get_logger


async def start_bot() -> None:
    """Start aiogram Telegram bot polling loop."""
    cfg = get_config().settings
    configure_logging(env=cfg.PULSE_ENV, log_level=cfg.LOG_LEVEL)
    logger = get_logger("pulse.bot")

    logger.info("starting_telegram_bot")
    bot = Bot(token=cfg.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    dp.message.outer_middleware(RateLimitMiddleware())
    dp.include_router(admin.router)
    dp.include_router(word.router)


    logger.info("bot_polling_started")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
