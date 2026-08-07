"""Daily winner selector."""


class WinnerCalculator:
    """Computes daily top voted guess for inclusion in next poster."""

    async def calculate_daily_winner(self, issue_id: str) -> str | None:
        """Find winning guess ID for issue.

        Returns:
            str | None: Winner guess ID if available.
        """
        raise NotImplementedError
