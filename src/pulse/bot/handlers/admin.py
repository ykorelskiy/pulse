"""Admin handlers module for Pulse bot."""

from datetime import datetime, timezone

from aiogram import Router, types
from aiogram.filters import Command

from pulse.briefsmith.builder import BriefBuilder
from pulse.config import get_config
from pulse.db.repo import WordsRepo
from pulse.digest.ranker import TopicRanker

router = Router()


def is_admin(user: types.User | None) -> bool:
    """Check if telegram user is admin (@anta9onist or matching ADMIN_CHAT_ID)."""
    if not user:
        return False
    cfg = get_config().settings
    if cfg.ADMIN_CHAT_ID and user.id == cfg.ADMIN_CHAT_ID:
        return True
    return bool(user.username and user.username.lower() == "anta9onist")


async def send_split_message(message: types.Message, text: str) -> None:
    """Send text split cleanly across messages without link previews."""
    no_preview = types.LinkPreviewOptions(is_disabled=True)

    if len(text) <= 3500:
        await message.answer(text, parse_mode="Markdown", link_preview_options=no_preview)
        return

    lines = text.split("\n")
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 <= 3500:
            current_chunk = f"{current_chunk}\n{line}".strip() if current_chunk else line
        else:
            if current_chunk:
                await message.answer(
                    current_chunk,
                    parse_mode="Markdown",
                    link_preview_options=no_preview,
                )
            current_chunk = line

    if current_chunk:
        await message.answer(current_chunk, parse_mode="Markdown", link_preview_options=no_preview)



@router.message(Command("show_words", "words"))
async def cmd_show_words(message: types.Message) -> None:
    """Show top reader submitted words with frequency count for admin."""
    if not is_admin(message.from_user):
        return

    repo = WordsRepo()
    recent = repo.get_recent_words(limit=200)

    if not recent:
        await message.answer("📊 **Топ слов от читателей:**\nСлов пока нет.")
        return

    counts: dict[str, int] = {}
    for entry in recent:
        w = entry.get("word", "").strip().lower()
        if w:
            counts[w] = counts.get(w, 0) + 1

    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]

    lines = ["📊 **Топ 20 фраз и слов от читателей за последнее время:**\n"]
    for idx, (word, cnt) in enumerate(sorted_words, 1):
        lines.append(f"{idx}. **{word}** — {cnt} шт.")

    lines.append(f"\nВсего получено фраз: {len(recent)}")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("show_news", "news"))
async def cmd_show_news(message: types.Message) -> None:
    """Show top 20 categorized news headlines for admin."""
    if not is_admin(message.from_user):
        return

    ranker = TopicRanker()
    categorized = ranker.get_categorized_news(items_per_category=3)

    lines = ["📰 **Топ новостей по 6 категориям:**"]
    for cat in categorized:
        lines.append(f"\n{cat['icon']} **{cat['title']} ({cat['weight']}):**")
        for idx, item in enumerate(cat["items"], 1):
            lines.append(f"  {idx}. [{item['source_name']}] [{item['headline']}]({item['url']})")

    text = "\n".join(lines)
    await send_split_message(message, text)


@router.message(Command("brief", "force_brief"))
async def cmd_force_brief(message: types.Message) -> None:
    """Generate and send today's daily author brief on-demand."""
    if not is_admin(message.from_user):
        return

    await message.answer("🔄 Генерирую свежий бриф дня с ИИ-отбором...")

    ranker = TopicRanker()
    top_10, top_50, source_stats = ranker.get_top_curated_digest(items_per_category=10, top_k=10)
    words = ranker.get_top_reader_words(limit=5)
    builder = BriefBuilder()

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    brief_text = builder.build_daily_brief(
        date_str=today_str,
        top_10_curated=top_10,
        top_50_flat=top_50,
        source_stats=source_stats,
        top_words=words,
    )


    await send_split_message(message, brief_text)
