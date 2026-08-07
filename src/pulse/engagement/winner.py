"""Daily winner selector."""

from pulse.db.repo import GuessesRepo


class WinnerCalculator:
    """Computes daily top voted guess for inclusion in next poster."""

    def __init__(self, guesses_repo: GuessesRepo | None = None) -> None:
        self.guesses_repo = guesses_repo or GuessesRepo()

    async def calculate_daily_winner(self, issue_id: str) -> str | None:
        """Find winning guess text for issue.

        Args:
            issue_id: Target issue UUID string.

        Returns:
            str | None: Winner guess text if available.
        """
        winning = self.guesses_repo.get_winning_guess(issue_id)
        if winning and isinstance(winning, dict):
            return winning.get("text")
        return None
