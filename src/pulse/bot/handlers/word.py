"""Word/phrase intake handlers for Telegram bot."""

import re

from aiogram import Router, types
from aiogram.filters import Command

from pulse.db.repo import UsersRepo, WordsRepo

router = Router()

# Allow words or short phrase combinations up to 30 characters
WORD_PATTERN = re.compile(r"^[a-zA-Zа-яА-ЯёЁ\s\-]{3,30}$")


def validate_word(raw_text: str) -> str | None:
    """Clean and validate reader's daily word/phrase submission (up to 30 chars).

    Args:
        raw_text: Raw input string from Telegram message.

    Returns:
        str | None: Cleaned lowercase phrase or None if invalid.
    """
    cleaned = raw_text.strip().lower()
    if cleaned.startswith("/word"):
        parts = cleaned.split(maxsplit=1)
        if len(parts) > 1:
            cleaned = parts[1].strip()
        else:
            return None

    if WORD_PATTERN.match(cleaned) and 3 <= len(cleaned) <= 30:
        return cleaned
    return None


@router.message(Command("start"))
@router.message(Command("help"))
async def cmd_start(message: types.Message) -> None:
    """Send detailed welcome message and all bot rules/commands."""
    text = (
        "🎨 **Привет! Я бот проекта «Пульс Дня».**\n\n"
        "Каждый день мы создаём сатирический дайджест-плакат по главным новостям "
        "и вашим ассоциациям.\n\n"
        "📜 **Правила участия:**\n"
        "1. **Окно приёма:** С **00:00 до 18:00 МСК**.\n"
        "   В 18:00 приём закрывается, и формируется бриф дня.\n"
        "2. **Формат:** Слово или короткое словосочетание **до 30 букв** (без цифр и эмодзи).\n"
        "3. **Лимит:** Ровно **1 словосочетание в календарный день**.\n\n"
        "🤖 **Доступные команды:**\n"
        "• `/start` или `/help` — вызвать эту справку и правила.\n"
        "• `/myword` — проверить, какую фразу вы отправили на сегодня.\n"
        "• `/word <фраза>` или просто напишите фразу в чат — отправить фразу дня.\n\n"
        "Присылай своё главное словосочетание дня прямо сейчас!"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("myword"))
async def cmd_myword(message: types.Message) -> None:
    """Show user's submitted word/phrase for today."""
    if not message.from_user:
        return

    words_repo = WordsRepo()
    recent = words_repo.get_recent_words(limit=100)
    user_words = [w for w in recent if w.get("user_id") == message.from_user.id]

    if user_words:
        latest = user_words[0]
        await message.answer(
            f"Ваше присланное словосочетание на сегодня: **«{latest['word']}»**",
            parse_mode="Markdown",
        )
    else:
        await message.answer("Вы ещё не отправляли словосочетание сегодня. Напишите его мне!")


@router.message()
async def process_word_submission(message: types.Message) -> None:
    """Process incoming text message as a daily word/phrase submission."""
    if not message.from_user or not message.text:
        return

    raw_text = message.text.strip()

    # Skip commands handled by other handlers
    if raw_text.startswith("/") and not raw_text.startswith("/word"):
        return

    word = validate_word(raw_text)
    if not word:
        await message.answer(
            "⚠️ Пожалуйста, пришлите слово или короткое словосочетание "
            "от 3 до 30 букв без цифр и эмодзи\n"
            "(например: *сатира*, *нейросеть*, *технологический прорыв*).",
            parse_mode="Markdown",
        )
        return

    # Record user and word in WordsRepo
    users_repo = UsersRepo()
    users_repo.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    words_repo = WordsRepo()
    words_repo.add_word(
        user_id=message.from_user.id,
        username=message.from_user.username,
        word=word,
    )

    await message.answer(
        f"✅ Отлично! Ваше словосочетание **«{word}»** принято для сегодняшнего плаката дня!",
        parse_mode="Markdown",
    )
