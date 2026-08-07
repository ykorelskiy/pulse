"""Daily guessing game winner selection job."""


async def run_winner_job() -> None:
    """Calculate winning user guess for current issue."""
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_winner_job())
