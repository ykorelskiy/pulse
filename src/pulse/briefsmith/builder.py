"""Author brief builder module."""


class BriefBuilder:
    """Constructs the daily concise brief for the author (Assisted Mode)."""

    def build_daily_brief(
        self,
        date_str: str,
        top_news: list[str],
        top_words: list[str],
        previous_winner_text: str | None = None,
    ) -> str:
        """Build short author brief containing context, words, and yesterday's winner.

        Returns:
            str: Formatted markdown brief for author.
        """
        raise NotImplementedError
