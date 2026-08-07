"""Hourly RSS collection job."""


async def run_collect_job() -> None:
    """Collect latest news headlines from active RSS feeds."""
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_collect_job())
