"""Publisher module for site_issues table and Supabase pulse-covers storage bucket."""

import io
from datetime import datetime, timezone
import zoneinfo
from PIL import Image

from pulse.config import get_config
from pulse.db.client import get_supabase_client
from pulse.logging import get_logger

logger = get_logger("pulse.publisher.site_publisher")
MSK_TZ = zoneinfo.ZoneInfo("Europe/Moscow")


from datetime import datetime, timedelta, timezone

def get_msk_today() -> str:
    """Return today date string in Europe/Moscow timezone (YYYY-MM-DD)."""
    return datetime.now(MSK_TZ).strftime("%Y-%m-%d")


def get_active_issue_date() -> str:
    """Return active target issue date string (YYYY-MM-DD).

    If today's issue is already published, shifts target to tomorrow's date.
    Otherwise returns today's date.
    """
    today_str = get_msk_today()
    try:
        client = get_supabase_client()
        res = client.table("site_issues").select("status,published").eq("issue_date", today_str).execute()
        rows = res.data or []
        if rows:
            row = rows[0]
            if row.get("status") == "published" or row.get("published") is True:
                dt = datetime.strptime(today_str, "%Y-%m-%d") + timedelta(days=1)
                return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning("get_active_issue_date_error", error=str(e))
    return today_str


def get_active_cycle_start_iso(target_date_str: str | None = None) -> str:
    """Return ISO timestamp string for the start of the current news cycle (18:00 MSK cutoff)."""
    if target_date_str:
        dt = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=MSK_TZ)
        start_msk = dt.replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(days=1)
        return start_msk.astimezone(timezone.utc).isoformat()
        
    now_msk = datetime.now(timezone.utc).astimezone(MSK_TZ)
    today_18msk = now_msk.replace(hour=18, minute=0, second=0, microsecond=0)
    if now_msk >= today_18msk:
        start_msk = today_18msk
    else:
        start_msk = today_18msk - timedelta(days=1)
    return start_msk.astimezone(timezone.utc).isoformat()


def has_valid_cover(image_path: str | None) -> bool:
    """Check if image_path represents a real uploaded cover (not a placeholder)."""
    return bool(image_path and image_path != "pending")


def resize_and_convert_to_webp(image_bytes: bytes, max_long_edge: int, quality: int = 80) -> bytes:
    """Resize image so its long edge <= max_long_edge and convert to WebP format."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        w, h = img.size
        long_edge = max(w, h)
        if long_edge > max_long_edge:
            scale = max_long_edge / float(long_edge)
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        out_io = io.BytesIO()
        img.save(out_io, format="WEBP", quality=quality, optimize=True)
        return out_io.getvalue()


def process_and_upload_cover(
    image_bytes: bytes,
    target_date_str: str | None = None,
    title: str | None = None,
    news_data: list | None = None,
    prompt: str | None = None,
    published: bool = True,
) -> dict[str, str]:
    """Process image, upload 3 WebP variants to Supabase Storage, and upsert site_issues row.

    Args:
        image_bytes: Raw bytes of uploaded cover image.
        target_date_str: Target issue date string (YYYY-MM-DD). Defaults to today in MSK.
        title: Optional title / theme of the issue.
        news_data: Optional list of top news items.
        prompt: Optional AI prompt used to generate the cover image.
        published: Whether issue is published immediately.

    Returns:
        dict: Summary of createdpaths and status.
    """
    if not target_date_str:
        target_date_str = get_msk_today()

    dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    year_str = dt.strftime("%Y")
    month_str = dt.strftime("%m")
    day_str = dt.strftime("%d")

    path_prefix = f"{year_str}/{month_str}/{day_str}"
    cover_path = f"{path_prefix}/cover.webp"
    thumb480_path = f"{path_prefix}/thumb-480.webp"
    thumb128_path = f"{path_prefix}/thumb-128.webp"

    # Generate 3 WebP variants
    cover_bytes = resize_and_convert_to_webp(image_bytes, max_long_edge=2048, quality=80)
    thumb480_bytes = resize_and_convert_to_webp(image_bytes, max_long_edge=480, quality=80)
    thumb128_bytes = resize_and_convert_to_webp(image_bytes, max_long_edge=128, quality=80)

    client = get_supabase_client()
    bucket_name = "pulse-covers"

    # Upload/upsert 3 files to Storage
    for p, b in [(cover_path, cover_bytes), (thumb480_path, thumb480_bytes), (thumb128_path, thumb128_bytes)]:
        try:
            client.storage.from_(bucket_name).upload(
                path=p,
                file=b,
                file_options={"cache-control": "max-age=3600", "content-type": "image/webp", "upsert": "true"},
            )
        except Exception as e:
            logger.warning("storage_upload_warning", path=p, error=str(e))

    # If news_data not provided, try to preserve existing news from DB if present
    if news_data is None:
        try:
            existing = client.table("site_issues").select("news").eq("issue_date", target_date_str).execute()
            if existing.data and existing.data[0].get("news"):
                news_data = existing.data[0]["news"]
        except Exception as e:
            logger.warning("fetch_existing_news_for_cover_warning", error=str(e))

    # Normalize news dicts to ensure both text & headline, source & source_name keys are present
    normalized_news = []
    if news_data:
        for item in news_data:
            if isinstance(item, dict):
                item_copy = dict(item)
                if not item_copy.get("text"):
                    item_copy["text"] = item_copy.get("headline") or item_copy.get("ru_headline") or item_copy.get("summary") or ""
                raw_src = item_copy.get("source") or item_copy.get("source_name") or "Источник"
                item_copy["source"] = raw_src.split(" — ")[0].split(" - ")[0].strip()
                normalized_news.append(item_copy)
            else:
                normalized_news.append(item)

    # Upsert site_issues table row
    issue_payload = {
        "issue_date": target_date_str,
        "image_path": cover_path,
        "thumb480_path": thumb480_path,
        "thumb128_path": thumb128_path,
        "title": title or f"Пульс дня — {dt.strftime('%d.%m.%Y')}",
        "news": normalized_news,
        "prompt": prompt,
        "published": published,
        "published_at": datetime.now(timezone.utc).isoformat() if published else None,
    }

    try:
        client.table("site_issues").upsert(issue_payload, on_conflict="issue_date").execute()
    except Exception as e:
        logger.error("site_issues_upsert_failed", error=str(e))
        raise e

    logger.info("site_issue_processed_success", date=target_date_str, cover_path=cover_path)
    return {
        "issue_date": target_date_str,
        "cover_path": cover_path,
        "thumb480_path": thumb480_path,
        "thumb128_path": thumb128_path,
        "status": "published" if published else "pending",
    }
