import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiogram import Bot, F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

from pulse.briefsmith.builder import BriefBuilder
from pulse.config import get_config
from pulse.db.repo import WordsRepo
from pulse.digest.ranker import TopicRanker
from pulse.logging import get_logger
from pulse.publisher.caption import CaptionBuilder
from pulse.publisher.orchestrator import MultiPublisherOrchestrator
from pulse.publisher.site_publisher import get_msk_today, process_and_upload_cover

logger = get_logger("pulse.bot.admin")
router = Router()


def save_admin_chat_id(user_id: int) -> None:
    """Auto-persist numeric admin chat ID to .env and runtime settings."""
    try:
        cfg = get_config().settings
        if cfg.ADMIN_CHAT_ID != user_id:
            cfg.ADMIN_CHAT_ID = user_id
            env_file = Path(".env")
            if env_file.exists():
                content = env_file.read_text(encoding="utf-8")
                if "ADMIN_CHAT_ID=" in content:
                    lines = [f"ADMIN_CHAT_ID={user_id}" if l.startswith("ADMIN_CHAT_ID=") else l for l in content.splitlines()]
                    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
                else:
                    env_file.write_text(content + f"\nADMIN_CHAT_ID={user_id}\n", encoding="utf-8")
    except Exception:
        pass


def is_admin(user: types.User | None) -> bool:
    """Check if telegram user is admin (@anta9onist or matching ADMIN_CHAT_ID)."""
    if not user:
        return False
    cfg = get_config().settings
    if cfg.ADMIN_CHAT_ID:
        try:
            if int(user.id) == int(cfg.ADMIN_CHAT_ID):
                return True
        except (ValueError, TypeError):
            pass
    if user.username and user.username.lower() == "anta9onist":
        save_admin_chat_id(user.id)
        return True
    return False


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
                        current_chunk, parse_mode=ParseMode.MARKDOWN, link_preview_options=no_preview
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
                current_chunk, parse_mode=ParseMode.MARKDOWN, link_preview_options=no_preview
            )
        except Exception:
            await message.answer(
                current_chunk, parse_mode=None, link_preview_options=no_preview
            )


@router.message(Command("brief"))
async def cmd_brief(message: types.Message) -> None:
    """Generate daily brief on demand and send to admin."""
    if not is_admin(message.from_user):
        return

    await message.answer("🔄 **Формирую бриф и отбор новостей...**")

    try:
        ranker = TopicRanker()
        top_10, top_50, source_stats = ranker.get_top_curated_digest(items_per_category=10, top_k=10)
        words_repo = WordsRepo()
        top_words = words_repo.get_active_words(limit=5)
        word_strings = [w["word"] for w in top_words]

        builder = BriefBuilder()
        today_str = get_msk_today()
        brief_text = builder.build_daily_brief(
            date_str=today_str,
            top_10_curated=top_10,
            top_50_flat=top_50,
            source_stats=source_stats,
            top_words=word_strings,
        )

        await send_split_message(message, brief_text)
    except Exception as e:
        logger.error("cmd_brief_failed", error=str(e))
        await message.answer(f"❌ Ошибка при генерации брифа: {e}")


@router.message(Command("word"))
async def cmd_add_word(message: types.Message) -> None:
    """Add a new word to reader guesses."""
    if not is_admin(message.from_user):
        return

    text = message.text or ""
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Использование: `/word <слово>`", parse_mode=ParseMode.MARKDOWN)
        return

    word = parts[1].strip()
    try:
        words_repo = WordsRepo()
        added = words_repo.add_word(word=word, source="author")
        await message.answer(f"✅ Слово **«{added['word']}»** добавлено в список отгадок!", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.answer(f"❌ Ошибка добавления слова: {e}")


async def send_full_post_preview(
    target_date: str,
    row: dict[str, Any],
    bot: Bot,
    chat_id: int,
) -> None:
    """Send photo + 15 news caption + publish button preview."""
    image_path = row.get("image_path") or row.get("thumb480_path")
    img_url = f"https://zyoznyeqvorhztrpgdjw.supabase.co/storage/v1/object/public/pulse-covers/{image_path}"

    builder = CaptionBuilder()
    caption = builder.build_caption(
        date_str=target_date,
        title=row.get("title"),
        news_items=row.get("news") or [],
    )

    publish_kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🚀 Опубликовать во все каналы (TG + VK + Сайт)",
                    callback_data=f"publish_all_{target_date}",
                )
            ]
        ]
    )

    [y, m, d] = target_date.split("-")
    short_caption = f"🖼 **ПУЛЬС ДНЯ — {d}.{m}.{y}**"
    text_body = caption
    if text_body.startswith("🖼 **ПУЛЬС ДНЯ"):
        lines = text_body.split("\n", 2)
        text_body = lines[-1].lstrip()

    await bot.send_photo(
        chat_id=chat_id,
        photo=img_url,
        caption=short_caption,
        parse_mode=ParseMode.MARKDOWN,
    )
    await bot.send_message(
        chat_id=chat_id,
        text=text_body,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=publish_kbd,
    )


@router.message(F.photo)
async def cmd_process_photo(message: types.Message) -> None:
    """Process uploaded poster photo, generate 3 sizes, and immediately send full post preview."""
    if not is_admin(message.from_user):
        return

    bot = message.bot
    if not bot:
        return

    caption_text = message.caption or ""
    parts = caption_text.strip().split(maxsplit=1)
    target_date = get_msk_today()
    prompt_text = None

    if len(parts) > 0 and len(parts[0]) == 10 and parts[0][4] == "-" and parts[0][7] == "-":
        target_date = parts[0]
        prompt_text = parts[1] if len(parts) > 1 else None
    else:
        prompt_text = caption_text if caption_text else None

    await message.answer(f"⚙️ **Обрабатываю обложку на {target_date} (генерирую 3 размера)...**")

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded = await bot.download_file(file_info.file_path)
        image_bytes = downloaded.read()

        res = process_and_upload_cover(
            image_bytes,
            target_date_str=target_date,
            prompt=prompt_text,
            published=False,
        )

        logger.info("cover_3_sizes_processed_successfully", date=target_date, paths=res)

        from pulse.db.client import get_supabase_client
        client = get_supabase_client()
        row_res = client.table("site_issues").select("*").eq("issue_date", target_date).execute()
        rows = row_res.data or []

        if rows:
            await send_full_post_preview(
                target_date=target_date,
                row=rows[0],
                bot=bot,
                chat_id=message.chat.id,
            )
        else:
            await message.answer(f"✅ **Обложка сохранена (3 размера сформированы)!**\nОбновляю запись выпуска...")

    except Exception as e:
        logger.error("process_photo_failed", error=str(e))
        await message.answer(f"❌ Ошибка при обработке картинки: {e}")


@router.message(Command("post"))
@router.message(Command("preview_post"))
async def cmd_preview_post(message: types.Message) -> None:
    """Send channel post preview if image uploaded, or latest top 15 news if no image yet."""
    if not is_admin(message.from_user):
        return

    bot = message.bot
    if not bot:
        return

    text = message.text or ""
    parts = text.strip().split()
    target_date = None
    if len(parts) > 1 and len(parts[1]) == 10 and parts[1][4] == "-" and parts[1][7] == "-":
        target_date = parts[1]

    if not target_date:
        target_date = get_msk_today()

    from pulse.db.client import get_supabase_client
    client = get_supabase_client()

    try:
        res = client.table("site_issues").select("*").eq("issue_date", target_date).execute()
        rows = res.data or []
        row = rows[0] if rows else None

        # Check if cover image has been uploaded
        if row and (row.get("image_path") or row.get("thumb480_path")):
            await send_full_post_preview(
                target_date=target_date,
                row=row,
                bot=bot,
                chat_id=message.chat.id,
            )
        else:
            # No cover image yet -> return latest 15 news items for today
            ranker = TopicRanker()
            top_10, top_50, _ = ranker.get_top_curated_digest(items_per_category=10, top_k=10)
            builder = CaptionBuilder()
            news_caption = builder.build_caption(
                date_str=target_date,
                news_items=top_50[:15],
            )
            header = f"📰 **АКТУАЛЬНЫЙ ТЕКСТ 15 НОВОСТЕЙ НА {target_date} (обложка еще не загружена):**\n\n"
            await send_split_message(message, header + news_caption)

    except Exception as e:
        logger.error("cmd_preview_post_failed", error=str(e))
        await message.answer(f"❌ Ошибка при подготовке предпросмотра: {e}")


@router.callback_query(F.data.startswith("publish_all_"))
async def cb_publish_all(callback: types.CallbackQuery) -> None:
    """Handle one-click multi-platform publication callback."""
    if not is_admin(callback.from_user):
        await callback.answer("⛔️ Недостаточно прав.", show_alert=True)
        return

    target_date = callback.data.replace("publish_all_", "").strip()
    await callback.answer("🚀 Запускаю изолированную автопубликацию...")

    from pulse.db.client import get_supabase_client
    client = get_supabase_client()

    res = client.table("site_issues").select("*").eq("issue_date", target_date).execute()
    rows = res.data or []
    if not rows:
        await callback.message.answer(f"⚠️ Выпуск на {target_date} не найден.")
        return

    row = rows[0]
    image_path = row.get("image_path") or row.get("thumb480_path")
    img_url = f"https://zyoznyeqvorhztrpgdjw.supabase.co/storage/v1/object/public/pulse-covers/{image_path}"
    news_items = row.get("news") or []

    await callback.message.answer(f"⏳ **Публикую выпуск за {target_date} во все соцсети...**")

    orchestrator = MultiPublisherOrchestrator()
    pub_results = await orchestrator.publish_all(
        issue_date=target_date,
        img_url=img_url,
        news_items=news_items,
        title=row.get("title"),
    )

    report_lines = [
        f"🎉 **ВЫПУСК ОТ {target_date} УСПЕШНО ОПУБЛИКОВАН!**",
        "",
    ]

    tg = pub_results.get("telegram", {})
    if tg.get("success"):
        report_lines.append(f"✅ **Telegram-канал:** [Перейти к посту]({tg['url']})")
    else:
        report_lines.append(f"❌ **Telegram-канал:** {tg.get('error')}")

    vk = pub_results.get("vk", {})
    if vk.get("success"):
        report_lines.append(f"✅ **ВКонтакте:** [Перейти к посту]({vk['url']})")
    else:
        report_lines.append(f"❌ **ВКонтакте:** {vk.get('error')}")

    site = pub_results.get("website", {})
    if site.get("success"):
        report_lines.append(f"✅ **Веб-сайт:** [Смотреть выпуск]({site['url']})")
    else:
        report_lines.append(f"❌ **Веб-сайт:** {site.get('error')}")

    await callback.message.answer(
        text="\n".join(report_lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
