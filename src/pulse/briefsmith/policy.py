"""Editorial policy filter for briefs (Direct Mode per user directive)."""


class EditorialPolicyEnforcer:
    """Enforces editorial guidelines.

    Note:
        Per user directive (2026-08-07), mandatory allegory transformations and
        politician face bans are disabled. Words and news phrases are passed directly.
    """

    def sanitize_input(
        self, top_news: list[str], top_words: list[str]
    ) -> tuple[list[str], list[str]]:
        """Pass news phrases and reader words directly.

        Returns:
            tuple[list[str], list[str]]: (sanitized_news, sanitized_words)
        """
        clean_news = [n.strip() for n in top_news if n.strip()]
        clean_words = [w.strip() for w in top_words if w.strip()]
        return clean_news, clean_words
