"""Bot rate limiting middleware for enforcing 1 word per 24 hours."""

from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from pulse.db.repo import WordsRepo


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
        if not hasattr(event, "from_user") or not hasattr(event, "text"):
            return await handler(event, data)


        text = event.text.strip()
        # Allow /start, /help, /myword without rate limiting
        if text.startswith(("/start", "/help", "/myword")):
            return await handler(event, data)

        user_id = event.from_user.id
        recent = self.words_repo.get_recent_words(limit=100)

        now = datetime.now(timezone.utc)
        for entry in recent:
            if entry.get("user_id") == user_id:
                created_raw = entry.get("created_at")
                if created_raw:
                    try:
                        created_dt = datetime.fromisoformat(created_raw)
                        if created_dt.tzinfo is None:
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        if now - created_dt < timedelta(hours=24):
                            await event.answer(
                                f"⏳ Вы уже присылали слово дня (**«{entry.get('word')}»**).\n"
                                "Следующее слово можно будет отправить через 24 часа "
                                "с момента предыдущего!",
                                parse_mode="Markdown",
                            )

                            return None
                    except ValueError:
                        pass

        return await handler(event, data)
