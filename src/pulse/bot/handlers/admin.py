import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiogram import Bot, F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

from pulse.bot.keyboards import build_top_selection_keyboard
from pulse.briefsmith.builder import BriefBuilder
from pulse.config import get_config
from pulse.db.repo import WordsRepo
from pulse.digest.ranker import TopicRanker
from pulse.logging import get_logger
from pulse.publisher.caption import CaptionBuilder
from pulse.publisher.orchestrator import MultiPublisherOrchestrator
from pulse.publisher.site_publisher import get_active_issue_date, get_msk_today, process_and_upload_cover

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


@router.message(Command("top"))
async def cmd_top_news(message: types.Message) -> None:
    """Send top N curated news items with rating scores to admin.

    Usage:
    /top -> top 15 news by New Model
    /top 20 -> top 20 news by New Model
    /top compare -> compare ranks between New Model (primary) and Legacy Model
    """
    if not is_admin(message.from_user):
        return

    text = (message.text or "").strip()
    parts = text.split()
    is_compare = len(parts) > 1 and parts[1].lower() == "compare"
    limit = 15
    if len(parts) > 1 and parts[1].isdigit():
        limit = min(max(int(parts[1]), 1), 50)

    target_date = get_active_issue_date()
    mode_str = "сравнение Новая vs Старая модель" if is_compare else f"ТОП-{limit}"
    await message.answer(f"📊 **Формирую {mode_str} позитивных новостей (дата выпуска: {target_date})...**")

    try:
        ranker = TopicRanker(target_date_str=target_date)

        if is_compare:
            comparison = ranker.get_legacy_vs_new_comparison(limit=limit)
            lines = [
                f"📊 **СРАВНЕНИЕ МОДЕЛЕЙ РАНЖИРОВАНИЯ ({target_date})**\n",
                "🥇 **Новая модель (CoT + Сентимент редактора)** vs 📜 **Старая модель**\n",
            ]
            for item in comparison:
                new_r = item["new_rank"]
                leg_r = item["legacy_rank"]
                hl = item["headline"]
                score = item["score"]
                lines.append(f"#{new_r} (в старой: #{leg_r}) | ⭐ **{score:.1f}** — {hl}")
            lines.append("\n💡 *Новая модель используется как ведущая для отбора новостей.*")
        else:
            _, top_50, _ = ranker.get_top_curated_digest(items_per_category=10, top_k=50)

            lines = [
                f"📊 **ТОП-{limit} ПОЗИТИВНЫХ НОВОСТЕЙ ДНЯ ({target_date})**\n",
                "📌 *Аналитическая подборка Новой модели (CoT + Сентимент редактора):*\n",
            ]

            for idx, item in enumerate(top_50[:limit], 1):
                raw_title = item.get("headline") or item.get("title") or item.get("text") or ""
                headline = raw_title.strip()
                url = item.get("url", "")
                score = item.get("total_score") or item.get("score") or 0.0

                score_str = f"⭐ **{score:.1f}**" if isinstance(score, (int, float)) and score > 0 else "⭐ **—**"

                if url and headline:
                    lines.append(f"{idx}. {score_str} — [{headline}]({url})")
                elif headline:
                    lines.append(f"{idx}. {score_str} — {headline}")
                elif url:
                    lines.append(f"{idx}. {score_str} — [{url}]({url})")

            lines.append("")
            lines.append("💡 *Сравнить с базовой моделью: `/top compare` | Изменить кол-во: `/top 20`*")

        full_response = "\n".join(lines)
        await send_split_message(message, full_response)
    except Exception as e:
        logger.error("cmd_top_failed", error=str(e))
        await message.answer(f"❌ Ошибка при получении ТОП новостей: {e}")


@router.message(Command("publish"))
async def cmd_publish_now(message: types.Message) -> None:
    """Instantly publish today's ready issue to all channels (TG + VK + Website)."""
    if not is_admin(message.from_user):
        return

    target_date = get_active_issue_date()
    await message.answer(f"🚀 **Проверяю готовность выпуска от {target_date} и запускаю публикацию...**")

    try:
        from pulse.jobs.auto_publish import run_auto_publish
        from pulse.db.client import get_supabase_client

        client = get_supabase_client()
        res = client.table("site_issues").select("*").eq("issue_date", target_date).execute()
        rows = res.data or []

        if not rows or not rows[0].get("image_path"):
            await message.answer(
                f"❌ **Выпуск от {target_date} еще не сформирован!**\n\n"
                "Для публикации необходимо сначала вызвать `/daily` и загрузить обложку."
            )
            return

        # Run publish job immediately
        await run_auto_publish()
        await message.answer(f"✅ **Команда публикации выпуска от {target_date} успешно выполнена!**")
    except Exception as e:
        logger.error("cmd_publish_now_failed", error=str(e))
        await message.answer(f"❌ Ошибка при выполнении публикации: {e}")



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

    news_items = row.get("news") or []
    builder = CaptionBuilder()
    caption = builder.build_caption(
        date_str=target_date,
        title=row.get("title"),
        news_items=news_items,
    )

    publish_kbd = build_top_selection_keyboard(
        issue_date=target_date,
        total_count=len(news_items),
    )

    [y, m, d] = target_date.split("-")
    short_caption = f"**ПУЛЬС ДНЯ — {d}.{m}.{y}**"
    text_body = caption
    if text_body.startswith("**ПУЛЬС ДНЯ") or text_body.startswith("🖼 **ПУЛЬС ДНЯ"):
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


@router.callback_query(F.data.startswith("top_t:"))
async def cb_toggle_top_item(query: types.CallbackQuery) -> None:
    """Toggle news item selection checkbox in top keyboard."""
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        await query.answer()
        return

    issue_date = parts[1]
    toggled_idx = int(parts[2])
    csv_selected = parts[3] if len(parts) > 3 and parts[3] != "none" else ""

    selected = {int(x) for x in csv_selected.split(",") if x.isdigit()}
    if toggled_idx in selected:
        selected.remove(toggled_idx)
    else:
        selected.add(toggled_idx)

    from pulse.db.client import get_supabase_client
    client = get_supabase_client()
    res = client.table("site_issues").select("news").eq("issue_date", issue_date).execute()
    total_count = 15
    if res.data and res.data[0].get("news"):
        total_count = len(res.data[0]["news"])

    new_kbd = build_top_selection_keyboard(
        issue_date=issue_date,
        total_count=total_count,
        selected_indices=selected,
    )

    try:
        if query.message:
            await query.message.edit_reply_markup(reply_markup=new_kbd)
    except Exception:
        pass
    await query.answer()


@router.callback_query(F.data.startswith("top_rm:"))
async def cb_remove_selected_top_items(query: types.CallbackQuery) -> None:
    """Remove selected news items from top issue and update DB + message text."""
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        await query.answer("Не выбрано ни одной новости", show_alert=True)
        return

    issue_date = parts[1]
    csv_selected = parts[2] if len(parts) > 2 and parts[2] != "none" else ""
    selected_indices = {int(x) for x in csv_selected.split(",") if x.isdigit()}

    if not selected_indices:
        await query.answer("Не выбрано ни одной новости", show_alert=True)
        return

    from pulse.db.client import get_supabase_client
    client = get_supabase_client()
    res = client.table("site_issues").select("*").eq("issue_date", issue_date).execute()
    if not res.data:
        await query.answer("Выпуск не найден в базе данных", show_alert=True)
        return

    row = res.data[0]
    current_news: list[dict[str, Any]] = row.get("news") or []

    # Filter out selected items
    filtered_news = [item for idx, item in enumerate(current_news, 1) if idx not in selected_indices]

    # Fill back to 15 if reserve news items available
    try:
        ranker = TopicRanker()
        _, top_50, _ = ranker.get_top_curated_digest(items_per_category=10, top_k=50)

        existing_urls = {
            n.get("url") or n.get("link")
            for n in filtered_news
            if n.get("url") or n.get("link")
        }
        for candidate in top_50:
            if len(filtered_news) >= 15:
                break
            cand_url = candidate.get("url") or candidate.get("link")
            if cand_url and cand_url not in existing_urls:
                filtered_news.append(candidate)
                existing_urls.add(cand_url)
    except Exception as e:
        logger.warning("failed_replenishing_reserve_news", error=str(e))

    # Update site_issues table in Supabase
    try:
        client.table("site_issues").update({"news": filtered_news}).eq("issue_date", issue_date).execute()
    except Exception as e:
        logger.error("failed_updating_news_after_removal", error=str(e))

    # Rebuild caption text
    builder = CaptionBuilder()
    caption = builder.build_caption(
        date_str=issue_date,
        title=row.get("title"),
        news_items=filtered_news,
    )

    text_body = caption
    if text_body.startswith("**ПУЛЬС ДНЯ") or text_body.startswith("🖼 **ПУЛЬС ДНЯ"):
        lines = text_body.split("\n", 2)
        text_body = lines[-1].lstrip()

    new_kbd = build_top_selection_keyboard(
        issue_date=issue_date,
        total_count=len(filtered_news),
        selected_indices=set(),
    )

    if query.message:
        try:
            await query.message.edit_text(
                text=text_body,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=new_kbd,
            )
        except Exception as e:
            logger.error("failed_editing_text_after_remove", error=str(e))

    await query.answer(f"Удалено {len(selected_indices)} новостей. ТОП обновлен!", show_alert=False)


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
    target_date = get_active_issue_date()
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

        from pulse.db.client import get_supabase_client
        client = get_supabase_client()

        # Retrieve news items for this date if already stored, or rank top 15 news for today
        news_data = None
        try:
            existing_res = client.table("site_issues").select("news").eq("issue_date", target_date).execute()
            if existing_res.data and existing_res.data[0].get("news"):
                news_data = existing_res.data[0]["news"]
        except Exception as e:
            logger.warning("fetch_existing_news_failed", error=str(e))

        if not news_data:
            try:
                ranker = TopicRanker(target_date_str=target_date)
                _, top_50, _ = ranker.get_top_curated_digest(items_per_category=10, top_k=10)
                news_data = top_50[:15]
            except Exception as e:
                logger.error("ranker_fetch_failed_for_photo", error=str(e))
                news_data = []

        res = process_and_upload_cover(
            image_bytes,
            target_date_str=target_date,
            news_data=news_data,
            prompt=prompt_text,
            published=False,
        )

        logger.info("cover_3_sizes_processed_successfully", date=target_date, paths=res)

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
        target_date = get_active_issue_date()

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
            ranker = TopicRanker(target_date_str=target_date)
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


MONTHS_RU = {
    1: "ЯНВАРЯ", 2: "ФЕВРАЛЯ", 3: "МАРТА", 4: "АПРЕЛЯ",
    5: "МАЯ", 6: "ИЮНЯ", 7: "ИЮЛЯ", 8: "АВГУСТА",
    9: "СЕНТЯБРЯ", 10: "ОКТЯБРЯ", 11: "НОЯБРЯ", 12: "ДЕКАБРЯ"
}

@router.message(Command("prompt"))
async def cmd_prompt(message: types.Message) -> None:
    """Generate the exact prompt text for the image generator."""
    if not is_admin(message.from_user):
        return

    text = message.text or ""
    parts = text.strip().split()
    target_date = None
    if len(parts) > 1 and len(parts[1]) == 10 and parts[1][4] == "-" and parts[1][7] == "-":
        target_date = parts[1]

    if not target_date:
        target_date = get_active_issue_date()

    try:
        ranker = TopicRanker(target_date_str=target_date)
        _, top_50, _ = ranker.get_top_curated_digest(items_per_category=10, top_k=10)
        news_items = top_50[:15]
        
        news_list = []
        for i, item in enumerate(news_items, 1):
            headline = (item.get("headline") or item.get("title") or item.get("text") or "").strip()
            headline = " ".join(headline.split())  # remove newlines
            if headline:
                news_list.append(f"{i}. {headline}")
        
        news_str = "\n".join(news_list)
        
        year, month, day = target_date.split("-")
        month_name = MONTHS_RU[int(month)]
        formatted_date = f"{int(day)} {month_name} {year}"
        
        prompt_text = (
            "Используй прикреплённый файл pulse_day_master_prompt.md как главный промпт.\n\n"
            "Используй первый референс для точного внешнего вида робота.\n"
            "Используй второй и третий референсы только для художественной стилистики и принципа композиции.\n\n"
            "ПЕРЕМЕННАЯ ТЕКУЩЕЙ ДАТЫ:\n"
            f"CURRENT_DATE = {formatted_date}\n\n"
            "ПЕРЕМЕННАЯ НОВОСТЕЙ:\n"
            "NEWS = \n\n"
            f"{news_str}\n\n"
            "Строго следуй master prompt.\n"
            "Особенно важно: дата CURRENT_DATE имеет приоритет над любыми датами, которые видны на референсных изображениях."
        )
        
        # Send without any markdown parsing so it's a raw string, easy to copy exactly
        await message.answer(prompt_text, parse_mode=None, disable_web_page_preview=True)

    except Exception as e:
        logger.error("cmd_prompt_failed", error=str(e))
        await message.answer(f"❌ Ошибка при генерации промпта: {e}")



@router.callback_query(F.data.startswith("confirm_publish_"))
async def cb_confirm_publish(callback: types.CallbackQuery) -> None:
    """Confirm publication — sets confirmed=true in DB. Actual publish happens at 20:00 MSK via cron."""
    if not is_admin(callback.from_user):
        await callback.answer("⛔️ Недостаточно прав.", show_alert=True)
        return

    target_date = callback.data.replace("confirm_publish_", "").strip()

    from pulse.db.client import get_supabase_client
    client = get_supabase_client()

    try:
        client.table("site_issues").update({"confirmed": True}).eq("issue_date", target_date).execute()
    except Exception as e:
        logger.error("confirm_publish_db_update_failed", error=str(e))

    await callback.answer("✅ Публикация подтверждена!")
    await callback.message.answer(
        f"✅ **Публикация «Пульс дня — {target_date}» подтверждена!**\n\n"
        f"Выпуск выйдет автоматически в **20:00 МСК** во все каналы (TG + VK + Сайт).",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(Command("reset"))
async def cmd_reset(message: types.Message) -> None:
    """Delete the saved issue data for a specific day to allow regenerating it."""
    if not is_admin(message.from_user):
        return

    text = message.text or ""
    parts = text.strip().split()
    target_date = None
    if len(parts) > 1 and len(parts[1]) == 10 and parts[1][4] == "-" and parts[1][7] == "-":
        target_date = parts[1]

    if not target_date:
        target_date = get_active_issue_date()

    from pulse.db.client import get_supabase_client
    client = get_supabase_client()
    try:
        client.table("site_issues").delete().eq("issue_date", target_date).execute()
        await message.answer(f"✅ Я успешно **обнулил** сохраненные данные выпуска за `{target_date}`!\n\nМожете присылать новую картинку — бот заново соберет самые свежие новости.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error("cmd_reset_failed", error=str(e))
        await message.answer(f"❌ Ошибка при удалении выпуска: {e}")


@router.message(Command("status"))
async def cmd_status(message: types.Message) -> None:
    """Show the current status of the target date issue."""
    if not is_admin(message.from_user):
        return

    text = message.text or ""
    parts = text.strip().split()
    target_date = None
    if len(parts) > 1 and len(parts[1]) == 10 and parts[1][4] == "-" and parts[1][7] == "-":
        target_date = parts[1]

    if not target_date:
        target_date = get_active_issue_date()

    from pulse.db.client import get_supabase_client
    client = get_supabase_client()
    try:
        res = client.table("site_issues").select("*").eq("issue_date", target_date).execute()
        rows = res.data or []
        
        if not rows:
            await message.answer(
                f"📊 **Статус выпуска на {target_date}:**\n\n"
                f"Выпуск абсолютно чист (ни новостей, ни обложки).\n"
                f"Отправьте боту картинку или нажмите `/prompt`, чтобы начать работу.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        row = rows[0]
        news_data = row.get("news") or []
        news_count = len(news_data)
        has_news = news_count > 0
        has_image = bool(row.get("image_path"))
        is_confirmed = bool(row.get("confirmed"))
        is_published = bool(row.get("published"))
        
        lines = [
            f"📊 **Статус выпуска на {target_date}:**\n",
            f"📰 **Новости зафиксированы:** {'✅ (' + str(news_count) + ' шт)' if has_news else '❌'}",
            f"🖼 **Обложка загружена:** {'✅' if has_image else '❌'}",
            f"⏳ **Публикация подтверждена:** {'✅ (Ждет отправки в 20:00)' if is_confirmed else '❌'}",
            f"🚀 **Опубликовано:** {'✅ (Уже вышло)' if is_published else '❌ (Еще не вышло)'}"
        ]
        
        await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error("cmd_status_failed", error=str(e))
        await message.answer(f"❌ Ошибка при получении статуса: {e}")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Show detailed help message for all admin commands."""
    if not is_admin(message.from_user):
        return

    help_text = (
        "🤖 **СПРАВОЧНИК КОМАНД АДМИНИСТРАТОРА:**\n\n"
        "🔸 `/status [дата]` — показать текущий статус подготовки выпуска (зафиксированы ли новости, загружена ли обложка, подтверждена ли публикация).\n"
        "   └ *Формат даты: `YYYY-MM-DD`. Если без аргумента — использует текущую активную дату.*\n\n"
        "🔸 `/prompt [дата]` — сгенерировать готовый промпт для нейросети с актуальными новостями.\n"
        "   └ *Например: `/prompt 2026-08-09`.*\n\n"
        "🔸 `/post [дата]` (или `/preview_post`) — посмотреть, как будет выглядеть текст или готовый пост на выбранный день.\n"
        "   └ *Например: `/post 2026-08-09`.*\n\n"
        "🔸 `/reset [дата]` — **ОБНУЛИТЬ** сохраненный выпуск за этот день.\n"
        "   └ *Удаляет новости и картинку из базы. Полезно, если вы хотите пересобрать выпуск вечером с новыми новостями.*\n\n"
        "🔸 `/top [количество]` — показать топ позитивных новостей (с оценками нейросети).\n"
        "   └ *Например: `/top 20` (по умолчанию показывает 15).*\n\n"
        "🔸 `/word <слово>` — добавить слово в список скрытых слов-отгадок.\n"
        "   └ *Например: `/word слон`.*\n\n"
        "🖼 **КАК ОПУБЛИКОВАТЬ ВЫПУСК:**\n"
        "Просто отправьте боту картинку. Бот сам обрежет её, прикрепит свежие новости (если их еще нет в базе на сегодня) и выдаст кнопку «Подтвердить публикацию в 20:00»."
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

