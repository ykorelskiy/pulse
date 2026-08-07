"""Daily brief construction job."""


async def run_daily_job() -> None:
    """Build daily author brief and send to admin Telegram chat."""
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_daily_job())
