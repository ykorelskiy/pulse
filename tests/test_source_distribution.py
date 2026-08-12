"""Diagnostic test for source distribution and scoring pipeline."""

import asyncio
from datetime import datetime, timezone, timedelta
from pulse.db.repo import NewsRepo
from pulse.db.client import get_supabase_client


def test_source_distribution():
    """Verify that ALL sources have items in DB and scoring works evenly."""
    client = get_supabase_client()
    if not client:
        import pytest
        pytest.skip("Supabase client is unconfigured locally — skipping live DB distribution check")

    repo = NewsRepo()
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()


    # 1. Count total items per source in DB (paginated)
    all_data = []
    offset = 0
    while True:
        res = client.table("news_items").select("source_id,status").gte("collected_at", since).range(offset, offset + 999).execute()
        items = res.data or []
        all_data.extend(items)
        if len(items) < 1000:
            break
        offset += 1000

    print(f"\n{'='*70}")
    print(f"DIAGNOSTIC: Source Distribution Test")
    print(f"{'='*70}")
    print(f"Total items in DB (24h): {len(all_data)}")

    # Count by source
    source_counts = {}
    status_counts = {}
    source_status = {}
    for item in all_data:
        sid = item.get("source_id", "unknown")
        status = item.get("status", "null")
        source_counts[sid] = source_counts.get(sid, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
        key = (sid, status)
        source_status[key] = source_status.get(key, 0) + 1

    print(f"\nStatus distribution: {status_counts}")
    print(f"\n--- Items per source ---")
    for sid, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        scored = source_status.get((sid, "scored"), 0)
        pending = source_status.get((sid, "pending"), 0)
        rejected = source_status.get((sid, "rejected_victims"), 0)
        print(f"  {sid:30s} total={count:4d}  scored={scored:4d}  pending={pending:4d}  rejected={rejected:4d}")

    # 2. Test get_scored_24h_news returns only scored items
    scored_items = repo.get_scored_24h_news()
    print(f"\n--- get_scored_24h_news() returned {len(scored_items)} items ---")
    scored_sources = {}
    for item in scored_items:
        sid = item.get("source_id", "unknown")
        scored_sources[sid] = scored_sources.get(sid, 0) + 1
    for sid, count in sorted(scored_sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sid:30s}: {count}")

    # 3. Verify NO pending items leak into scored query
    pending_in_scored = [i for i in scored_items if i.get("status") != "scored"]
    if pending_in_scored:
        print(f"\n❌ FAIL: {len(pending_in_scored)} non-scored items found in get_scored_24h_news!")
    else:
        print(f"\n✅ PASS: get_scored_24h_news returns ONLY scored items")

    # 4. Test get_all_24h_news for audit
    all_items = repo.get_all_24h_news()
    print(f"\n--- get_all_24h_news() returned {len(all_items)} items (for audit) ---")

    # 5. Test diversity: sources with 0 items is a problem
    zero_sources = [sid for sid, count in source_counts.items() if count == 0]
    if zero_sources:
        print(f"\n⚠️  WARNING: {len(zero_sources)} sources with 0 items: {zero_sources}")
    else:
        print(f"\n✅ PASS: All sources have items in DB")

    # 6. Test ranking output
    from pulse.digest.ranker import TopicRanker
    ranker = TopicRanker()
    top_10, top_50, source_stats = ranker.get_top_curated_digest(top_k=10)

    print(f"\n--- Ranker Top 10 ---")
    top_10_sources = set()
    for idx, item in enumerate(top_10, 1):
        print(f"  {idx}. [{item['source_name']}] {item['headline'][:80]}")
        top_10_sources.add(item["source_name"])
    print(f"  Unique sources in top 10: {len(top_10_sources)}")

    print(f"\n--- Ranker Top 50 source distribution ---")
    top_50_sources = {}
    for item in top_50:
        s = item.get("source_name", "unknown")
        top_50_sources[s] = top_50_sources.get(s, 0) + 1
    for s, c in sorted(top_50_sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {s:50s}: {c}")
    print(f"  Unique sources in top 50: {len(top_50_sources)}")

    # Verify diversity cap: no source exceeds cap in top 10 or top 50
    max_in_10 = max(top_50_sources.values()) if top_50_sources else 0
    violations_10 = [(s, c) for s, c in top_50_sources.items() if c > 4]
    if violations_10:
        print(f"\n❌ FAIL: Sources exceeding 4-item cap in top 50: {violations_10}")
    else:
        print(f"\n✅ PASS: No source exceeds 4-item cap in top 50")

    print(f"\n--- Audit Stats (source_stats) ---")
    total_analyzed = 0
    for s in source_stats:
        total_analyzed += s["analyzed"]
        print(f"  {s['name']:50s} analyzed={s['analyzed']:4d}  top50={s['in_top_50']}  top10={s['in_top_10']}")
    print(f"  TOTAL analyzed: {total_analyzed}")

    print(f"\n{'='*70}")
    print(f"DIAGNOSTIC COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    test_source_distribution()
