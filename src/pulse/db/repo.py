"""Supabase Repositories layer with persistent local JSON fallback storage."""

import contextlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from supabase import Client

from pulse.db.client import get_supabase_client

# Local persistent JSON fallback file for when live Supabase is unconfigured
FALLBACK_FILE = Path.cwd() / "data" / "words_fallback.json"


def _load_fallback_words() -> list[dict[str, Any]]:
    """Load words from persistent local JSON file."""
    if not FALLBACK_FILE.exists():
        return []
    try:
        with open(FALLBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_fallback_word(entry: dict[str, Any]) -> None:
    """Save word entry to persistent local JSON file."""
    try:
        FALLBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        words = _load_fallback_words()
        words.insert(0, entry)
        with open(FALLBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(words[:200], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# Global reference for backward compatibility
MEMORY_WORDS_STORE = _load_fallback_words()


class DuplicateIssueError(Exception):
    """Raised when an issue for the specified date already exists."""

    pass


class BaseRepo:
    """Base repository class wrapping Supabase client."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Client | None:
        if self._client is None:
            return get_supabase_client()
        return self._client


class UsersRepo(BaseRepo):
    """Repository for user management."""

    def upsert_user(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        if not self.client:
            return data

        try:
            res = self.client.table("users").upsert(data).execute()
            return res.data[0] if res.data else data
        except Exception:
            return data

    def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        if not self.client:
            return None
        try:
            res = self.client.table("users").select("*").eq("id", user_id).execute()
            return res.data[0] if res.data else None
        except Exception:
            return None


class WordsRepo(BaseRepo):
    """Repository for reader word submissions with persistent local fallback."""

    def add_word(
        self,
        user_id: int,
        username: str | None,
        word: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "user_id": user_id,
            "username": username,
            "word": word,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        # Save to persistent local JSON fallback file
        _save_fallback_word(data)

        if not self.client:
            return data

        try:
            res = self.client.table("words").insert(data).execute()
            return res.data[0] if res.data else data
        except Exception:
            return data

    def get_recent_words(self, limit: int = 50) -> list[dict[str, Any]]:
        db_words: list[dict[str, Any]] = []
        if self.client:
            try:
                res = (
                    self.client.table("words")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                db_words = res.data or []
            except Exception:
                db_words = []

        local_words = _load_fallback_words()
        combined = db_words + local_words
        seen = set()
        unique_list = []
        for item in combined:
            key = (item.get("user_id"), item.get("word"), item.get("created_at"))
            if key not in seen:
                seen.add(key)
                unique_list.append(item)

        return unique_list[:limit]


class NewsRepo(BaseRepo):
    """Repository for news articles."""

    def add_source(
        self,
        source_id: str,
        name: str,
        url: str,
        category: str = "general",
    ) -> dict[str, Any]:
        data = {
            "id": source_id,
            "name": name,
            "url": url,
            "category": category,
        }
        if not self.client:
            return data
        try:
            res = self.client.table("sources").upsert(data).execute()
            return res.data[0] if res.data else data
        except Exception:
            return data

    @staticmethod
    def clean_url(url: str) -> str:
        """Strip UTM parameters and tracking query strings from URL."""
        if not url:
            return url
        import urllib.parse as urlparse
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qsl(parsed.query)
        filtered_query = [
            (k, v) for k, v in query
            if not k.startswith("utm_") and k not in ("fbclid", "gclid", "yclid", "ref")
        ]
        new_query = urlparse.urlencode(filtered_query)
        cleaned = urlparse.urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
        return cleaned

    @staticmethod
    def compute_headline_hash(headline: str) -> str:
        """Compute MD5 hash of normalized headline (lowercase, trimmed, collapsed spaces)."""
        import hashlib
        import re
        normalized = re.sub(r"\s+", " ", headline.lower().strip())
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def add_article(
        self,
        source_id: str,
        headline: str,
        url: str,
        published_at: str | None = None,
        summary: str = "",
    ) -> dict[str, Any]:
        clean_u = self.clean_url(url)
        h_hash = self.compute_headline_hash(headline)

        data: dict[str, Any] = {
            "source_id": source_id,
            "headline": headline,
            "headline_hash": h_hash,
            "url": clean_u,
            "published_at": published_at,
            "status": "pending",
        }
        if summary:
            data["summary"] = summary

        if not self.client:
            return data

        try:
            # Dual deduplication check
            # 1. By URL
            existing_url = (
                self.client.table("news_items")
                .select("*")
                .eq("url", clean_u)
                .limit(1)
                .execute()
            )
            if existing_url and getattr(existing_url, "data", None):
                return existing_url.data[0]

            # 2. By (source_id, headline_hash)
            existing_headline = (
                self.client.table("news_items")
                .select("*")
                .eq("source_id", source_id)
                .eq("headline_hash", h_hash)
                .limit(1)
                .execute()
            )
            if existing_headline and getattr(existing_headline, "data", None):
                return existing_headline.data[0]

            res = self.client.table("news_items").insert(data).execute()
            return res.data[0] if res.data else data
        except Exception:
            # Fallback upsert if insert raises constraint error
            with contextlib.suppress(Exception):
                res = self.client.table("news_items").upsert(data, on_conflict="url").execute()
                return res.data[0] if res.data else data
            return data

    def get_pending_news(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch news items waiting for LLM scoring."""
        if not self.client:
            return []
        try:
            res = (
                self.client.table("news_items")
                .select("*")
                .eq("status", "pending")
                .order("collected_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception:
            return []

    def get_scored_24h_news(self) -> list[dict[str, Any]]:
        """Fetch all scored news items from the floating last 24 hours with pagination."""
        if not self.client:
            return []
        try:
            from datetime import timedelta
            since_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            all_items: list[dict[str, Any]] = []
            page_size = 1000
            offset = 0
            while True:
                res = (
                    self.client.table("news_items")
                    .select("*")
                    .gte("collected_at", since_iso)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                items = getattr(res, "data", []) or []
                all_items.extend(items)
                if len(items) < page_size:
                    break
                offset += page_size
            return all_items
        except Exception:
            pass
        return self.get_latest_news(limit=200)

    def update_scored_article(self, article_id: str, update_data: dict[str, Any]) -> None:
        """Update scored article fields in Supabase."""
        if not self.client:
            return
        try:
            self.client.table("news_items").update(update_data).eq("id", article_id).execute()
        except Exception:
            pass

    def mark_items_used_and_archived(
        self,
        issue_id: str,
        used_ids: list[str],
        archived_ids: list[str],
    ) -> None:
        """Mark winner items as 'used' and remaining cluster items as 'archived'."""
        if not self.client:
            return
        try:
            if used_ids:
                self.client.table("news_items").update({
                    "status": "used",
                    "used_in_issue_id": issue_id,
                }).in_("id", used_ids).execute()

            if archived_ids:
                self.client.table("news_items").update({
                    "status": "archived",
                    "used_in_issue_id": issue_id,
                }).in_("id", archived_ids).execute()
        except Exception:
            pass

    def get_latest_news(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self.client:
            return []
        try:
            res = (
                self.client.table("news_items")
                .select("*")
                .order("collected_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception:
            return []


class IssuesRepo(BaseRepo):
    """Repository for daily poster issues."""

    def create_for_date(
        self,
        issue_date: str,
        brief_used: str | None = None,
        status: str = "draft",
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "date": issue_date,
            "brief_used": brief_used,
            "status": status,
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        if not self.client:
            return data

        # Check existing date to guarantee DuplicateIssueError
        existing = (
            self.client.table("issues").select("id").eq("date", issue_date).execute()
        )
        if existing and getattr(existing, "data", None) and len(existing.data) > 0:
            raise DuplicateIssueError(
                f"An issue for date {issue_date} already exists."
            )

        res = self.client.table("issues").insert(data).execute()
        return res.data[0] if res.data else data

    def get_by_date(self, issue_date: str) -> dict[str, Any] | None:
        if not self.client:
            return None
        try:
            res = self.client.table("issues").select("*").eq("date", issue_date).execute()
            return res.data[0] if res.data else None
        except Exception:
            return None


class BriefsRepo(BaseRepo):
    """Repository for brief generation history."""

    def save_brief(
        self,
        issue_id: str,
        brief_text: str,
        top_words: list[str] | None = None,
        top_news: list[str] | None = None,
    ) -> dict[str, Any]:
        data = {
            "issue_id": issue_id,
            "brief_text": brief_text,
            "top_words": top_words or [],
            "top_news": top_news or [],
        }
        if not self.client:
            return data

        res = self.client.table("briefs_history").insert(data).execute()
        return res.data[0] if res.data else data


class GuessesRepo(BaseRepo):
    """Repository for user decoding guesses."""

    def add_guess(
        self,
        issue_id: str,
        user_id: int,
        username: str | None,
        text: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "issue_id": issue_id,
            "user_id": user_id,
            "username": username,
            "text": text,
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        if not self.client:
            return data

        res = self.client.table("guesses").insert(data).execute()
        return res.data[0] if res.data else data

    def get_winning_guess(self, issue_id: str) -> dict[str, Any] | None:
        if not self.client:
            return None
        try:
            res = (
                self.client.table("guesses")
                .select("*")
                .eq("issue_id", issue_id)
                .order("votes", desc=True)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception:
            return None


class ReserveRepo(BaseRepo):
    """Repository for reserve backup posters."""

    def get_available(self) -> dict[str, Any] | None:
        if not self.client:
            return None
        try:
            res = (
                self.client.table("reserve_posters")
                .select("*")
                .eq("is_used", False)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception:
            return None


class OrdersRepo(BaseRepo):
    """Repository for commercial poster orders."""

    def create_order(
        self,
        customer_tg: str,
        tier_id: str,
        brief_description: str,
        amount: Decimal,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "customer_tg": customer_tg,
            "tier_id": tier_id,
            "brief_description": brief_description,
            "amount": float(amount),
            "status": "pending",
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        if not self.client:
            return data

        res = self.client.table("orders").insert(data).execute()
        return res.data[0] if res.data else data


class EventsRepo(BaseRepo):
    """Repository for system audit events."""

    def log_event(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        issue_id: str | None = None,
        user_id: int | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "event_type": event_type,
            "payload": payload or {},
            "issue_id": issue_id,
            "user_id": user_id,
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        if not self.client:
            return data

        res = self.client.table("events").insert(data).execute()
        return res.data[0] if res.data else data
