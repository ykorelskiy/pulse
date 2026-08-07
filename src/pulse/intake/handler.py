"""Intake workflow handler."""


class PosterIntakeHandler:
    """Handles author image upload, web version generation, and R2 storage."""

    async def process_author_upload(
        self, issue_id: str, image_bytes: bytes, filename: str
    ) -> tuple[str, str]:
        """Process high-resolution author upload and generate web version.

        Returns:
            tuple[str, str]: (hires_url, web_url)
        """
        raise NotImplementedError
