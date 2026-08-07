"""Tests for pulse.config module."""

from pathlib import Path
import pytest
from pydantic import ValidationError
from pulse.config import ConfigManager, Settings


def test_config_loads_with_valid_env(set_env_vars):
    """Test that ConfigManager successfully loads settings when required env vars exist."""
    cfg = ConfigManager(base_dir=Path.cwd())
    assert cfg.settings.PULSE_ENV == "testing"
    assert cfg.settings.SUPABASE_URL == "https://test.supabase.co"
    assert cfg.settings.ADMIN_CHAT_ID == 999888777


def test_missing_required_env_raises_validation_error(monkeypatch):
    """Test that missing required environment variables raises ValidationError."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    with pytest.raises((ValidationError, Exception)):
        Settings()


def test_masked_config_output(capsys, set_env_vars):
    """Test printing masked configuration output."""
    cfg = ConfigManager(base_dir=Path.cwd())
    cfg.print_masked_config()

    captured = capsys.readouterr()
    assert "PULSE CONFIGURATION CHECK" in captured.out
    assert "Status: OK" in captured.out
    assert "https://test.supabase.co" in captured.out
    assert "test-secret-key" not in captured.out
