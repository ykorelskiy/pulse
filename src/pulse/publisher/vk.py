"""VKontakte community publisher implementing native wall photo posting and fallback wall post via VK API v5.199."""

import asyncio
from pathlib import Path
from typing import Any

import httpx

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

        async with httpx.AsyncClient(timeout=30.0) as client:
            photo_attachment_id: str | None = None

            # Attempt photo upload if image provided
            if image_input:
                try:
                    image_bytes: bytes
                    if isinstance(image_input, bytes):
                        image_bytes = image_input
                    elif isinstance(image_input, str) and (image_input.startswith("http://") or image_input.startswith("https://")):
                        res = await client.get(image_input)
                        res.raise_for_status()
                        image_bytes = res.content
                    else:
                        image_bytes = Path(image_input).read_bytes()

                    # 1. Get Wall Upload Server URL
                    upload_server_url = "https://api.vk.com/method/photos.getWallUploadServer"
                    params = {
                        "group_id": gid,
                        "access_token": self.access_token,
                        "v": VK_API_VERSION,
                    }
                    res_server = await client.get(upload_server_url, params=params)
                    data_server = res_server.json()

                    if "response" in data_server and "upload_url" in data_server["response"]:
                        upload_url = data_server["response"]["upload_url"]

                        # 2. Upload photo bytes to VK Upload Server
                        files = {"photo": ("cover.jpg", image_bytes, "image/jpeg")}
                        res_upload = await client.post(upload_url, files=files)
                        upload_result = res_upload.json()

                        if upload_result.get("photo") and upload_result.get("photo") != "[]":
                            # 3. Save Wall Photo
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

                            if "response" in data_save and len(data_save["response"]) > 0:
                                saved_photo = data_save["response"][0]
                                photo_attachment_id = f"photo{saved_photo['owner_id']}_{saved_photo['id']}"
                    else:
                        err_msg = data_server.get("error", {}).get("error_msg", str(data_server))
                        logger.warning("vk_photo_upload_skipped_due_to_scope", error=err_msg)
                except Exception as e:
                    logger.warning("vk_photo_upload_failed_fallback_to_text", error=str(e))

            # 4. Post to Community Wall
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
