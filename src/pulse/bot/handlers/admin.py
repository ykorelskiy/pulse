import asyncio
from datetime import datetime, timezone

from aiogram import Bot, F, Router, types
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
    """Send text split cleanly across messages with fallback parsing and sleep delay."""
    no_preview = types.LinkPreviewOptions(is_disabled=True)

    lines = text.split("\n")
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 <= 3000:
            current_chunk = f"{current_chunk}\n{line}".strip() if current_chunk else line
        else:
            if current_chunk:
                try:
                    await message.answer(
                        current_chunk, parse_mode="Markdown", link_preview_options=no_preview
                    )
                except Exception:
                    await message.answer(
                        current_chunk, parse_mode=None, link_preview_options=no_preview
                    )
                await asyncio.sleep(0.3)
            current_chunk = line

    if current_chunk:
        try:
            await message.answer(
                current_chunk, parse_mode="Markdown", link_preview_options=no_preview
            )
        except Exception:
            await message.answer(
                current_chunk, parse_mode=None, link_preview_options=no_preview
            )





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


@router.message(F.photo)
async def handle_photo_cover_upload(message: types.Message, bot: Bot) -> None:
    """Handle photo upload by admin for site cover issue."""
    if not is_admin(message.from_user):
        return

    caption = (message.caption or "").strip()
    target_date = None
    prompt_text = None

    if caption:
        lines = caption.split("\n", 1)
        first_line = lines[0].strip()
        if len(first_line) == 10 and first_line[4] == "-" and first_line[7] == "-":
            target_date = first_line
            prompt_text = lines[1].strip() if len(lines) > 1 else None
        else:
            prompt_text = caption

    await message.answer("🖼 Принял картинку! Генерирую превью (WebP), сохраняю промпт и загружаю в хранилище сайта...")

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded = await bot.download_file(file_info.file_path)
        image_bytes = downloaded.read()

        from pulse.publisher.site_publisher import process_and_upload_cover
        res = process_and_upload_cover(
            image_bytes,
            target_date_str=target_date,
            prompt=prompt_text,
            published=True,
        )

        await message.answer(
            f"✅ **Выпуск успешно опубликован на сайте!**\n\n"
            f"📅 **Дата:** `{res['issue_date']}`\n"
            f"✍️ **Промпт:** `{prompt_text or 'Не указан'}`\n"
            f"🖼 **Обложка:** `{res['cover_path']}`"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при публикации картинки: {e}")


@router.message(Command("post"))
@router.message(Command("preview_post"))
async def cmd_preview_post(message: types.Message) -> None:
    """Send channel post preview (photo + formatted text) to admin."""
    if not is_admin(message.from_user):
        return

    text = message.text or ""
    parts = text.strip().split()
    target_date = None
    if len(parts) > 1 and len(parts[1]) == 10 and parts[1][4] == "-" and parts[1][7] == "-":
        target_date = parts[1]

    from pulse.publisher.site_publisher import get_msk_today
    if not target_date:
        target_date = get_msk_today()

    from pulse.db.client import get_supabase_client
    client = get_supabase_client()

    try:
        res = client.table("site_issues").select("*").eq("issue_date", target_date).execute()
        rows = res.data or []
        if not rows:
            await message.answer(
                f"⚠️ **Выпуск на {target_date} еще не сформирован!**\n\n"
                f"Отправьте боту изображение с подписью, чтобы создать выпуск."
            )
            return

        row = rows[0]
        image_path = row.get("thumb480_path") or row.get("image_path")
        if not image_path:
            await message.answer(f"⚠️ Для даты {target_date} нет загруженного изображения.")
            return

        from pulse.publisher.caption import CaptionBuilder
        builder = CaptionBuilder()
        caption = builder.build_caption(
            date_str=target_date,
            title=row.get("title"),
            news_items=row.get("news") or [],
        )

        img_url = f"https://zyoznyeqvorhztrpgdjw.supabase.co/storage/v1/object/public/pulse-covers/{image_path}"

        await message.answer_photo(
            photo=img_url,
            caption=caption,
            parse_mode="Markdown",
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при подготовке поста: {e}")
