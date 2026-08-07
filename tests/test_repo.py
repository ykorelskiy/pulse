"""Tests for pulse.db repositories."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from pulse.db.repo import (
    DuplicateIssueError,
    EventsRepo,
    IssuesRepo,
    NewsRepo,
    OrdersRepo,
    UsersRepo,
    WordsRepo,
)


def test_users_repo_upsert(mock_supabase):
    mock_res = MagicMock()
    mock_res.data = [{"id": 12345, "username": "testuser", "tenant_id": None}]
    mock_supabase.table().upsert().execute.return_value = mock_res

    repo = UsersRepo(client=mock_supabase)
    user = repo.upsert_user(12345, username="testuser")

    assert user["id"] == 12345
    assert user["username"] == "testuser"
    mock_supabase.table.assert_called_with("users")


def test_words_repo_add_word(mock_supabase):
    mock_res = MagicMock()
    mock_res.data = [{"id": "uuid-1", "user_id": 12345, "word": "сатира"}]
    mock_supabase.table().insert().execute.return_value = mock_res

    repo = WordsRepo(client=mock_supabase)
    res = repo.add_word(12345, "testuser", "сатира")

    assert res["word"] == "сатира"
    mock_supabase.table.assert_called_with("words")


def test_news_repo_add_article(mock_supabase):
    mock_res = MagicMock()
    mock_res.data = [{"id": "uuid-2", "headline": "Тест новость", "url": "http://ex.com/1"}]
    mock_supabase.table().insert().execute.return_value = mock_res

    repo = NewsRepo(client=mock_supabase)
    res = repo.add_article("rbc", "Тест новость", "http://ex.com/1")

    assert res["headline"] == "Тест новость"
    mock_supabase.table.assert_called_with("news_items")


def test_issues_repo_duplicate_error(mock_supabase):
    mock_res_existing = MagicMock()
    mock_res_existing.data = [{"id": "existing-issue-uuid"}]
    mock_supabase.table().select().eq().execute.return_value = mock_res_existing

    repo = IssuesRepo(client=mock_supabase)
    with pytest.raises(DuplicateIssueError):
        repo.create_for_date("2026-08-07")


def test_issues_repo_create_success():
    client = MagicMock()
    mock_select = MagicMock()
    mock_select.data = []

    mock_insert = MagicMock()
    mock_insert.data = [{"id": "new-issue-uuid", "date": "2026-08-07", "status": "draft"}]

    client.table().select().eq().execute.return_value = mock_select
    client.table().insert().execute.return_value = mock_insert

    repo = IssuesRepo(client=client)
    res = repo.create_for_date("2026-08-07", brief_used="Short brief")

    assert res["date"] == "2026-08-07"
    assert res["status"] == "draft"




def test_orders_repo_create_order(mock_supabase):
    mock_res = MagicMock()
    mock_res.data = [{"id": "order-1", "amount": 5000.0, "customer_tg": "@customer"}]
    mock_supabase.table().insert().execute.return_value = mock_res

    repo = OrdersRepo(client=mock_supabase)
    res = repo.create_order("@customer", "personal", "Personal brief", Decimal("5000.00"))

    assert res["amount"] == 5000.0
    mock_supabase.table.assert_called_with("orders")


def test_events_repo_log_event(mock_supabase):
    mock_res = MagicMock()
    mock_res.data = [{"id": "event-1", "event_type": "issue_published"}]
    mock_supabase.table().insert().execute.return_value = mock_res

    repo = EventsRepo(client=mock_supabase)
    res = repo.log_event("issue_published", payload={"date": "2026-08-07"})

    assert res["event_type"] == "issue_published"
    mock_supabase.table.assert_called_with("events")
