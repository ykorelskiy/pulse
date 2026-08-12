"""Supabase client singleton initialization."""

import logging

from supabase import Client, create_client

from pulse.config import get_config

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None


def is_supabase_configured() -> bool:
    """Check if Supabase credentials are valid live credentials."""
    try:
        cfg = get_config().settings
        url = cfg.SUPABASE_URL
        return not (
            not url
            or "placeholder" in url
            or "test-project" in url
            or "your-project-ref" in url
            or "test.supabase" in url
        )


    except Exception:
        return False


def get_supabase_client() -> Client | None:
    """Get lazy singleton Supabase client instance.

    Prefers SUPABASE_SERVICE_ROLE_KEY (bypasses RLS, safe for server-side use).
    Falls back to SUPABASE_KEY (anon) with a warning if service_role is not set.

    Returns:
        Client | None: Initialized Supabase client or None if unconfigured.
    """
    global _supabase_client
    if not is_supabase_configured():
        return None

    if _supabase_client is None:
        cfg = get_config().settings
        # Prefer service_role key (bypasses RLS, safe for server-side use)
        key = cfg.SUPABASE_SERVICE_ROLE_KEY or cfg.SUPABASE_KEY
        if not cfg.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY is not set — using anon key. "
                "This will fail if RLS is enabled on tables."
            )
        _supabase_client = create_client(cfg.SUPABASE_URL, key)
    return _supabase_client


def reset_supabase_client() -> None:
    """Reset singleton instance (useful for testing)."""
    global _supabase_client
    _supabase_client = None
