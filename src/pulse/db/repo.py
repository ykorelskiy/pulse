"""Supabase Repositories layer."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from supabase import Client
from pulse.db.client import get_supabase_client


class DuplicateIssueError(Exception):
    """Raised when an issue for the specified date already exists."""

    pass


class BaseRepo:
    """Base repository class wrapping Supabase client."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Client:
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
            "updated_at": datetime.now().isoformat(),
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        res = self.client.table("users").upsert(data).execute()
        return res.data[0] if res.data else data

    def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        res = self.client.table("users").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None


class WordsRepo(BaseRepo):
    """Repository for reader word submissions."""

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
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        res = self.client.table("words").insert(data).execute()
        return res.data[0] if res.data else data

    def get_recent_words(self, limit: int = 10) -> list[dict[str, Any]]:
        res = (
            self.client.table("words")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []


class NewsRepo(BaseRepo):
    """Repository for news articles."""

    def add_article(
        self,
        source_id: str,
        headline: str,
        url: str,
        published_at: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "source_id": source_id,
            "headline": headline,
            "url": url,
            "published_at": published_at,
        }
        res = self.client.table("news_items").insert(data).execute()
        return res.data[0] if res.data else data

    def get_latest_news(self, limit: int = 10) -> list[dict[str, Any]]:
        res = (
            self.client.table("news_items")
            .select("*")
            .order("collected_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []


class IssuesRepo(BaseRepo):
    """Repository for daily poster issues."""

    def create_for_date(
        self,
        issue_date: str,
        brief_used: str | None = None,
        status: str = "draft",
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        # Check existing date to guarantee DuplicateIssueError
        existing = (
            self.client.table("issues").select("id").eq("date", issue_date).execute()
        )
        if existing and getattr(existing, "data", None) and len(existing.data) > 0:
            raise DuplicateIssueError(
                f"An issue for date {issue_date} already exists."
            )

        data = {
            "date": issue_date,
            "brief_used": brief_used,
            "status": status,
        }
        if tenant_id:
            data["tenant_id"] = tenant_id

        res = self.client.table("issues").insert(data).execute()
        return res.data[0] if res.data else data

    def get_by_date(self, issue_date: str) -> dict[str, Any] | None:
        res = self.client.table("issues").select("*").eq("date", issue_date).execute()
        return res.data[0] if res.data else None


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

        res = self.client.table("guesses").insert(data).execute()
        return res.data[0] if res.data else data

    def get_winning_guess(self, issue_id: str) -> dict[str, Any] | None:
        res = (
            self.client.table("guesses")
            .select("*")
            .eq("issue_id", issue_id)
            .order("votes", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None


class ReserveRepo(BaseRepo):
    """Repository for reserve backup posters."""

    def get_available() -> dict[str, Any] | None:
        res = (
            self.client.table("reserve_posters")
            .select("*")
            .eq("is_used", False)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None


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

        res = self.client.table("events").insert(data).execute()
        return res.data[0] if res.data else data
