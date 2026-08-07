"""Votes counter."""


class VoteManager:
    """Manages voting reactions and upvotes on user guesses."""

    async def register_vote(self, guess_id: str, voter_user_id: int) -> int:
        """Register upvote for a guess.

        Returns:
            int: Updated vote count.
        """
        raise NotImplementedError
