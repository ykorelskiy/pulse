"""Cloudflare R2 storage client and Pillow image processing."""

from io import BytesIO
from typing import Any
import boto3
from PIL import Image
from pulse.config import get_config


class R2StorageClient:
    """Wrapper over Cloudflare R2 S3-compatible API using boto3."""

    def __init__(self, s3_client: Any | None = None) -> None:
        self._s3_client = s3_client

    @property
    def s3_client(self) -> Any:
        if self._s3_client is None:
            cfg = get_config().settings
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=cfg.R2_ENDPOINT_URL,
                aws_access_key_id=cfg.R2_ACCESS_KEY_ID,
                aws_secret_access_key=cfg.R2_SECRET_ACCESS_KEY,
            )
        return self._s3_client

    def upload(
        self, data: bytes, key: str, content_type: str = "image/png"
    ) -> str:
        """Upload raw binary data to Cloudflare R2 bucket.

        Args:
            data: Binary payload.
            key: Target object key in bucket.
            content_type: MIME type of uploaded file.

        Returns:
            str: Public CDN URL of uploaded asset.
        """
        cfg = get_config().settings
        self.s3_client.put_object(
            Bucket=cfg.R2_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"{cfg.R2_PUBLIC_DOMAIN.rstrip('/')}/{key.lstrip('/')}"


def make_web_version(data: bytes, max_long_edge: int = 2048, quality: int = 88) -> bytes:
    """Resize high-res poster image for web serving using Pillow.

    Args:
        data: Raw image byte array.
        max_long_edge: Maximum allowed long edge in pixels.
        quality: JPEG compression quality (1-100).

    Returns:
        bytes: Compressed web-optimized JPEG byte array.
    """
    with Image.open(BytesIO(data)) as img:
        img = img.convert("RGB")
        w, h = img.size
        long_edge = max(w, h)

        if long_edge > max_long_edge:
            scale = max_long_edge / float(long_edge)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        out_buffer = BytesIO()
        img.save(out_buffer, format="JPEG", quality=quality, optimize=True)
        return out_buffer.getvalue()


def generate_issue_key(date_str: str, is_web: bool = False) -> str:
    """Generate structured S3 storage key for issue poster.

    Example:
        `issues/2026/08/2026-08-07-hires.png`
        `issues/2026/08/2026-08-07-web.jpg`
    """
    parts = date_str.split("-")
    year = parts[0] if len(parts) > 0 else "2026"
    month = parts[1] if len(parts) > 1 else "08"
    suffix = "web.jpg" if is_web else "hires.png"
    return f"issues/{year}/{month}/{date_str}-{suffix}"
