"""Bot rate limiting middleware for enforcing 1 word/phrase per 24 hours."""

from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from pulse.db.repo import WordsRepo

# In-memory fallback storage when Supabase database is unreachable
MEMORY_WORDS_STORE: list[dict[str, Any]] = []


class RateLimitMiddleware(BaseMiddleware):
    """Middleware preventing users from submitting more than 1 word per 24 hours."""

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

        # Allow /start, /help, /myword without rate limiting
        if text.startswith(("/start", "/help", "/myword")):
            return await handler(event, data)

        user_id = from_user.id

        recent: list[dict[str, Any]] = []
        try:
            recent = self.words_repo.get_recent_words(limit=100)
        except Exception:
            recent = MEMORY_WORDS_STORE

        now = datetime.now(timezone.utc)
        for entry in recent:
            if entry.get("user_id") == user_id:
                created_raw = entry.get("created_at")
                if created_raw:
                    try:
                        created_dt = (
                            datetime.fromisoformat(created_raw)
                            if isinstance(created_raw, str)
                            else created_raw
                        )
                        if created_dt.tzinfo is None:
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        if now - created_dt < timedelta(hours=24):
                            w_val = entry.get("word")
                            await event.answer(
                                f"⏳ Вы уже присылали фразы дня (**«{w_val}»**).\n"
                                "Следующую фразу можно будет отправить через 24 часа "
                                "с момента предыдущей!",
                                parse_mode="Markdown",
                            )

                            return None

                    except Exception:
                        pass

        return await handler(event, data)
