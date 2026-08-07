"""Guesses submission handler."""


class GuessesHandler:
    """Processes user poster decoding submissions."""

    async def submit_guess(
        self, issue_id: str, user_id: int, username: str | None, text: str
    ) -> str:
        """Submit user guess version.

        Returns:
            str: Created guess ID.
        """
        raise NotImplementedError
