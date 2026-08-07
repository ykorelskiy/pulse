"""Bot rate limiting and time window middleware (00:00 - 18:00 MSK window)."""

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from zoneinfo import ZoneInfo

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from pulse.db.repo import MEMORY_WORDS_STORE, WordsRepo

MSK_TZ = ZoneInfo("Europe/Moscow")


class RateLimitMiddleware(BaseMiddleware):
    """Middleware enforcing 00:00-18:00 MSK intake window and 1 phrase per calendar day."""

    def __init__(self, words_repo: WordsRepo | None = None) -> None:
        self.words_repo = words_repo or WordsRepo()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        raw_text = getattr(event, "text", None)
        if not from_user or not raw_text:
            return await handler(event, data)

        text = raw_text.strip()
        # Allow /start, /help, /myword and admin commands without rate/window limiting
        if text.startswith(
            (
                "/start",
                "/help",
                "/myword",
                "/show_words",
                "/words",
                "/show_news",
                "/news",
                "/brief",
                "/force_brief",
            )
        ):
            return await handler(event, data)


        msk_now = datetime.now(timezone.utc).astimezone(MSK_TZ)
        today_date_str = msk_now.strftime("%Y-%m-%d")

        # 1. Check time window (00:00 - 18:00 MSK)
        if msk_now.hour >= 18:
            await event.answer(
                "⏳ **Приём фраз на сегодняшний плакат закрыт в 18:00 МСК.**\n"
                "⚠️ *Ваша фраза НЕ была сохранена*, так как бриф дня уже сформирован.\n\n"
                "Приходите после полуночи (с 00:00 МСК), чтобы отправить словосочетание "
                "на завтрашний плакат дня!",
                parse_mode="Markdown",
            )
            return None


        # 2. Check 1 submission per calendar day
        user_id = from_user.id
        recent: list[dict[str, Any]] = []
        try:
            recent = self.words_repo.get_recent_words(limit=100)
        except Exception:
            recent = MEMORY_WORDS_STORE

        for entry in recent:
            if entry.get("user_id") == user_id:
                created_raw = entry.get("created_at")
                if created_raw:
                    try:
                        if isinstance(created_raw, str):
                            c_dt = datetime.fromisoformat(created_raw)
                        else:
                            c_dt = created_raw
                        if c_dt.tzinfo is None:
                            c_dt = c_dt.replace(tzinfo=timezone.utc)
                        entry_msk_date = c_dt.astimezone(MSK_TZ).strftime("%Y-%m-%d")
                        if entry_msk_date == today_date_str:
                            w_val = entry.get("word")
                            await event.answer(
                                f"⏳ Вы уже присылали фразу на сегодня (**«{w_val}»**).\n"
                                "Новое словосочетание можно будет отправить завтра с 00:00 МСК!",
                                parse_mode="Markdown",
                            )
                            return None
                    except Exception:
                        pass

        return await handler(event, data)
