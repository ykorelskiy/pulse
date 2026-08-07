"""Admin-only commands for author @anta9onist to inspect news, words, and trigger briefs."""

from aiogram import Router, types
from aiogram.filters import Command

from pulse.briefsmith.builder import BriefBuilder
from pulse.config import get_config
from pulse.db.repo import NewsRepo, WordsRepo
from pulse.digest.ranker import TopicRanker

router = Router()


def is_admin(user: types.User | None) -> bool:
    """Check if user is authorized admin/author (@anta9onist or matching ADMIN_CHAT_ID)."""
    if not user:
        return False
    cfg = get_config().settings
    if user.id == cfg.ADMIN_CHAT_ID:
        return True
    return bool(user.username and user.username.lower() == "anta9onist")



@router.message(Command("show_words", "words"))
async def cmd_show_words(message: types.Message) -> None:
    """Show top reader words/phrases submitted today with frequency counts."""
    if not is_admin(message.from_user):
        return

    words_repo = WordsRepo()
    recent = words_repo.get_recent_words(limit=200)

    if not recent:
        await message.answer("ℹ️ В базе пока нет присланных слов за сегодня.")
        return

    # Count occurrences of phrases
    counter: dict[str, int] = {}
    for entry in recent:
        w = entry.get("word")
        if w:
            counter[w] = counter.get(w, 0) + 1

    sorted_words = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:20]

    lines = ["📊 **Топ слов и словосочетаний от читателей за сегодня:**\n"]
    for idx, (word, count) in enumerate(sorted_words, 1):
        lines.append(f"{idx}. **«{word}»** — {count} раз(а)")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("show_news", "news"))
async def cmd_show_news(message: types.Message) -> None:
    """Show top 10 news headlines and extracted key phrases for today."""
    if not is_admin(message.from_user):
        return

    news_repo = NewsRepo()
    latest_news = news_repo.get_latest_news(limit=20)
    ranker = TopicRanker(news_repo=news_repo)
    top_phrases = ranker.get_top_news_phrases(limit=10)

    lines = ["📰 **Топ фраз и новостей за сегодня:**\n"]
    lines.append("🔹 **Сформированные ключевые фразы:**")
    for idx, phrase in enumerate(top_phrases, 1):
        lines.append(f"  {idx}. **{phrase}**")

    if latest_news:
        lines.append("\n📌 **Свежие заголовки RSS:**")
        for idx, art in enumerate(latest_news[:10], 1):
            headline = art.get("headline", "")
            url = art.get("url", "#")
            lines.append(f"  {idx}. [{headline}]({url})")

    await message.answer("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)


@router.message(Command("brief", "force_brief"))
async def cmd_force_brief(message: types.Message) -> None:
    """Generate and send today's daily author brief on-demand."""
    if not is_admin(message.from_user):
        return

    await message.answer("🔄 Генерирую свежий бриф дня...")

    ranker = TopicRanker()
    news_details = ranker.get_top_news_details(limit=5)
    words = ranker.get_top_reader_words(limit=5)
    builder = BriefBuilder()

    from datetime import datetime, timezone
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    brief_text = builder.build_daily_brief(
        date_str=today_str,
        top_news=news_details,
        top_words=words,
    )


    await message.answer(brief_text, parse_mode="Markdown")
