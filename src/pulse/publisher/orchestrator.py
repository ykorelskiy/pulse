"""Multi-platform publisher orchestrator with error isolation."""

import asyncio
from typing import Any

from aiogram import Bot, types
from aiogram.enums import ParseMode

from pulse.config import get_config
from pulse.db.client import get_supabase_client
from pulse.logging import get_logger
from pulse.publisher.caption import CaptionBuilder
from pulse.publisher.vk import VKPublisher

logger = get_logger("pulse.publisher.orchestrator")


class MultiPublisherOrchestrator:
    """Orchestrates isolated publishing across Telegram, VK, and Website."""

    def __init__(self) -> None:
        self.cfg = get_config().settings

    async def publish_telegram_channel(
        self,
        img_url: str,
        caption: str,
    ) -> str:
        """Publish post to Telegram channel."""
        channel_id = self.cfg.CHANNEL_CHAT_ID
        if not channel_id:
            raise ValueError("CHANNEL_CHAT_ID is not configured.")

        bot = Bot(token=self.cfg.TELEGRAM_BOT_TOKEN)
        try:
            if len(caption) <= 1000:
                msg = await bot.send_photo(
                    chat_id=channel_id,
                    photo=img_url,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                )
                post_id = msg.message_id
            else:
                lines = caption.split("\n")
                header = lines[0]
                short_caption = f"🖼 **{header}**"
                text_body = caption
                if text_body.startswith(header):
                    text_body = text_body[len(header):].lstrip()

                await bot.send_photo(
                    chat_id=channel_id,
                    photo=img_url,
                    caption=short_caption,
                    parse_mode=ParseMode.MARKDOWN,
                )
                msg2 = await bot.send_message(
                    chat_id=channel_id,
                    text=text_body,
                    parse_mode=ParseMode.MARKDOWN,
                    link_preview_options=types.LinkPreviewOptions(is_disabled=True),
                )
                post_id = msg2.message_id

            clean_channel = str(channel_id).replace("@", "")
            if clean_channel.startswith("-100"):
                clean_channel = clean_channel[4:]
            url = f"https://t.me/{clean_channel}/{post_id}"
            return url
        finally:
            await bot.session.close()

    async def publish_vkontakte(
        self,
        date_str: str,
        img_url: str,
        news_items: list[dict[str, Any]],
    ) -> str:
        """Publish post to VKontakte community wall."""
        vk_pub = VKPublisher()
        vk_text = vk_pub.format_vk_post_text(
            date_str=date_str,
            news_items=news_items,
        )
        return await vk_pub.publish_issue(image_input=img_url, text=vk_text)

    async def publish_website(
        self,
        date_str: str,
    ) -> str:
        """Set issue status to published on Website showcase."""
        client = get_supabase_client()
        client.table("site_issues").update({"published": True}).eq("issue_date", date_str).execute()
        [y, m, d] = date_str.split("-")
        return f"http://192.109.206.42:8081/{y}/{m}/{d}"

    async def publish_all(
        self,
        issue_date: str,
        img_url: str,
        news_items: list[dict[str, Any]],
        title: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Publish issue across all platforms with fault isolation.

        Returns:
            dict mapping platform_id -> {"success": bool, "url": str|None, "error": str|None}
        """
        builder = CaptionBuilder()
        tg_caption = builder.build_caption(
            date_str=issue_date,
            title=title,
            news_items=news_items,
        )

        results: dict[str, dict[str, Any]] = {}

        # 1. Telegram Channel task
        async def run_tg():
            try:
                url = await self.publish_telegram_channel(img_url, tg_caption)
                return {"success": True, "url": url, "error": None}
            except Exception as e:
                logger.error("tg_channel_publish_error", error=str(e))
                return {"success": False, "url": None, "error": str(e)}

        # 2. VKontakte task
        async def run_vk():
            try:
                url = await self.publish_vkontakte(issue_date, img_url, news_items)
                return {"success": True, "url": url, "error": None}
            except Exception as e:
                logger.error("vk_publish_error", error=str(e))
                return {"success": False, "url": None, "error": str(e)}

        # 3. Website task
        async def run_site():
            try:
                url = await self.publish_website(issue_date)
                return {"success": True, "url": url, "error": None}
            except Exception as e:
                logger.error("site_publish_error", error=str(e))
                return {"success": False, "url": None, "error": str(e)}

        tg_res, vk_res, site_res = await asyncio.gather(
            run_tg(),
            run_vk(),
            run_site(),
            return_exceptions=False,
        )

        results["telegram"] = tg_res
        results["vk"] = vk_res
        results["website"] = site_res

        return results
