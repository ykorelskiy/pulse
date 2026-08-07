"""Supabase client singleton initialization."""

from supabase import Client, create_client

from pulse.config import get_config

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

    Returns:
        Client | None: Initialized Supabase client or None if unconfigured.
    """
    global _supabase_client
    if not is_supabase_configured():
        return None

    if _supabase_client is None:
        cfg = get_config().settings
        _supabase_client = create_client(cfg.SUPABASE_URL, cfg.SUPABASE_KEY)
    return _supabase_client


def reset_supabase_client() -> None:
    """Reset singleton instance (useful for testing)."""
    global _supabase_client
    _supabase_client = None
