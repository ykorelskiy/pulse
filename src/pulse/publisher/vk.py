"""VKontakte community publisher implementing native wall photo posting via VK API v5.199."""

import asyncio
import io
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from pulse.config import get_config
from pulse.logging import get_logger

logger = get_logger("pulse.publisher.vk")

VK_API_VERSION = "5.199"


class VKPublisher:
    """Publishes daily poster issues to VKontakte community wall."""

    def __init__(
        self,
        access_token: str | None = None,
        group_id: int | None = None,
    ) -> None:
        cfg = get_config().settings
        self.access_token = access_token or cfg.VK_ACCESS_TOKEN
        self.group_id = group_id or cfg.VK_GROUP_ID

    def format_vk_post_text(
        self,
        date_str: str,
        news_items: list[dict[str, Any]],
        site_url: str = "http://192.109.206.42:8081",
    ) -> str:
        """Format 15 news items with clickable source links for VK wall post.

        Args:
            date_str: Date string YYYY-MM-DD.
            news_items: List of news item dicts.
            site_url: Showcase website URL.

        Returns:
            str: Formatted VK wall post text.
        """
        [y, m, d] = date_str.split("-")
        formatted_date = f"{d}.{m}.{y}"

        lines = [
            f"🖼 ПУЛЬС ДНЯ — {formatted_date}",
            "",
            "📌 Главные позитивные новости дня:",
            "",
        ]

        if news_items:
            for idx, item in enumerate(news_items[:15], 1):
                headline = item.get("text") or item.get("ru_headline") or item.get("headline", "")
                url = item.get("url") or item.get("link", "")
                
                if url:
                    lines.append(f"{idx}. {headline}\n🔗 {url}\n")
                else:
                    lines.append(f"{idx}. {headline}\n")
        else:
            lines.append("Ежедневный выпуск отрывного календаря.\n")

        lines.append(f"📅 Интерактивный календарь: {site_url}/{y}/{m}/{d}")
        lines.append("💬 Telegram-канал: https://t.me/a_daily_pulse")

        return "\n".join(lines)

    async def publish_issue(
        self,
        image_input: str | bytes | None,
        text: str,
    ) -> str:
        """Publish image poster and formatted digest text to VK community wall.

        Args:
            image_input: Optional File path (str/Path), URL (str), or raw bytes of image.
            text: Wall post text message.

        Returns:
            str: Public VK wall post URL (e.g. https://vk.com/wall-240745088_12).
        """
        if not self.access_token or not self.group_id:
            raise ValueError("VK_ACCESS_TOKEN and VK_GROUP_ID must be configured for VK publishing.")

        gid = abs(int(self.group_id))

        async with httpx.AsyncClient(timeout=90.0) as client:
            photo_attachment_id: str | None = None

            # 1. Prepare and optimize photo
            if image_input:
                try:
                    raw_bytes: bytes
                    if isinstance(image_input, bytes):
                        raw_bytes = image_input
                    elif isinstance(image_input, str) and (image_input.startswith("http://") or image_input.startswith("https://")):
                        res = await client.get(image_input)
                        res.raise_for_status()
                        raw_bytes = res.content
                    else:
                        raw_bytes = Path(image_input).read_bytes()

                    # Convert WebP/PNG/etc. to optimized JPEG for VK API compliance
                    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                    if img.width > 1600 or img.height > 1600:
                        img.thumbnail((1600, 1600))
                    jpeg_io = io.BytesIO()
                    img.save(jpeg_io, format="JPEG", quality=88, optimize=True)
                    jpeg_bytes = jpeg_io.getvalue()
                    logger.info("vk_image_converted_to_jpeg", size_bytes=len(jpeg_bytes))

                    # 2. Get Wall Upload Server URL
                    upload_server_url = "https://api.vk.com/method/photos.getWallUploadServer"
                    params = {
                        "group_id": gid,
                        "access_token": self.access_token,
                        "v": VK_API_VERSION,
                    }
                    res_server = await client.get(upload_server_url, params=params)
                    data_server = res_server.json()

                    if "response" not in data_server or "upload_url" not in data_server["response"]:
                        err_msg = data_server.get("error", {}).get("error_msg", str(data_server))
                        logger.error("vk_get_upload_server_failed", error=err_msg)
                        raise RuntimeError(f"VK photos.getWallUploadServer failed: {err_msg}")

                    upload_url = data_server["response"]["upload_url"]

                    # 3. Upload JPEG photo bytes to VK Upload Server
                    files = {"photo": ("cover.jpg", jpeg_bytes, "image/jpeg")}
                    res_upload = await client.post(upload_url, files=files)
                    upload_result = res_upload.json()

                    if not upload_result.get("photo") or upload_result.get("photo") == "[]":
                        logger.error("vk_upload_server_empty_photo", response=upload_result)
                        raise RuntimeError("VK Upload Server returned empty photo field.")

                    # 4. Save Wall Photo
                    save_url = "https://api.vk.com/method/photos.saveWallPhoto"
                    save_params = {
                        "group_id": gid,
                        "photo": upload_result["photo"],
                        "server": upload_result["server"],
                        "hash": upload_result["hash"],
                        "access_token": self.access_token,
                        "v": VK_API_VERSION,
                    }
                    res_save = await client.post(save_url, data=save_params)
                    data_save = res_save.json()

                    if "response" not in data_save or len(data_save["response"]) == 0:
                        err_msg = data_save.get("error", {}).get("error_msg", str(data_save))
                        logger.error("vk_save_wall_photo_failed", error=err_msg)
                        raise RuntimeError(f"VK photos.saveWallPhoto failed: {err_msg}")

                    saved_photo = data_save["response"][0]
                    owner_id = saved_photo.get("owner_id")
                    photo_id = saved_photo.get("id")
                    access_key = saved_photo.get("access_key")

                    photo_attachment_id = f"photo{owner_id}_{photo_id}"
                    if access_key:
                        photo_attachment_id += f"_{access_key}"

                    logger.info("vk_photo_uploaded_attachment_id", attachment_id=photo_attachment_id)

                except Exception as e:
                    logger.error("vk_photo_upload_critical_error", error=str(e))
                    raise RuntimeError(f"Не удалось загрузить обложку плаката в ВК: {e}")

            # 5. Post to Community Wall
            post_url = "https://api.vk.com/method/wall.post"
            post_params: dict[str, Any] = {
                "owner_id": -gid,
                "from_group": 1,
                "message": text,
                "access_token": self.access_token,
                "v": VK_API_VERSION,
            }
            if photo_attachment_id:
                post_params["attachments"] = photo_attachment_id

            res_post = await client.post(post_url, data=post_params)
            data_post = res_post.json()

            if "error" in data_post:
                err_msg = data_post["error"].get("error_msg", str(data_post["error"]))
                logger.error("vk_wall_post_failed", error=err_msg)
                raise RuntimeError(f"VK API error (wall.post): {err_msg}")

            post_id = data_post["response"]["post_id"]
            final_vk_url = f"https://vk.com/wall-{gid}_{post_id}"
            logger.info("vk_post_published_successfully", post_url=final_vk_url)
            return final_vk_url
