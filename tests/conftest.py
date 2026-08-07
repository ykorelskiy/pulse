"""Pytest fixtures for offline unit testing."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set mandatory environment variables for tests."""
    monkeypatch.setenv("PULSE_ENV", "testing")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-anon-key-1234567890")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://account.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABCDEFTestToken")
    monkeypatch.setenv("ADMIN_CHAT_ID", "999888777")


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock

    # Default query chain mocks
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock

    res = MagicMock()
    res.data = []
    table_mock.execute.return_value = res

    return client


@pytest.fixture
def mock_s3():
    """Create a mock boto3 S3 client."""
    s3_client = MagicMock()
    s3_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    return s3_client
