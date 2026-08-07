"""Telegram channel publisher."""


class TelegramPublisher:
    """Posts approved poster issues to public Telegram channel."""

    async def publish_issue(
        self, channel_id: int, image_url: str, caption: str
    ) -> int:
        """Publish poster to channel.

        Returns:
            int: Sent Telegram message ID.
        """
        raise NotImplementedError
