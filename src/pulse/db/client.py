"""Supabase client singleton initialization."""

from typing import Any
from supabase import Client, create_client
from pulse.config import get_config

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Get lazy singleton Supabase client instance.

    Returns:
        Client: Initialized Supabase client.
    """
    global _supabase_client
    if _supabase_client is None:
        cfg = get_config().settings
        _supabase_client = create_client(cfg.SUPABASE_URL, cfg.SUPABASE_KEY)
    return _supabase_client


def reset_supabase_client() -> None:
    """Reset singleton instance (useful for testing)."""
    global _supabase_client
    _supabase_client = None
