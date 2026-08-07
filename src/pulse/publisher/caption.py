"""Post caption builder."""


class CaptionBuilder:
    """Builds channel post captions including winner attribution and tags."""

    def build_caption(
        self, date_str: str, winner_username: str | None = None
    ) -> str:
        """Build formatted Telegram post caption.

        Returns:
            str: Telegram post caption text.
        """
        raise NotImplementedError
