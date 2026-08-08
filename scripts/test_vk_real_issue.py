import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from pulse.db.client import get_supabase_client
from pulse.publisher.site_publisher import get_msk_today
from pulse.publisher.vk import VKPublisher


async def publish_real_today_issue():
    today_date = get_msk_today()
    print(f"Fetching real issue data from Supabase for date: {today_date}...")

    client = get_supabase_client()
    res = client.table("site_issues").select("*").eq("issue_date", today_date).execute()
    rows = res.data or []

    if not rows:
        # Fallback to latest available issue
        res_latest = client.table("site_issues").select("*").order("issue_date", desc=True).limit(1).execute()
        rows = res_latest.data or []

    if not rows:
        print("❌ No issue found in Supabase.")
        return

    row = rows[0]
    issue_date = row["issue_date"]
    image_path = row.get("image_path") or row.get("thumb480_path")
    news_items = row.get("news") or []

    print(f"Issue found for date {issue_date}. Image path: {image_path}. News count: {len(news_items)}")

    img_url = f"https://zyoznyeqvorhztrpgdjw.supabase.co/storage/v1/object/public/pulse-covers/{image_path}"

    publisher = VKPublisher()
    vk_text = publisher.format_vk_post_text(
        date_str=issue_date,
        news_items=news_items,
    )

    try:
        vk_url = await publisher.publish_issue(
            image_input=img_url,
            text=vk_text,
        )
        print(f"🎉 REAL ISSUE PUBLISHED TO VK: {vk_url}")
    except Exception as e:
        print(f"❌ Failed to publish real issue: {e}")


if __name__ == "__main__":
    asyncio.run(publish_real_today_issue())
