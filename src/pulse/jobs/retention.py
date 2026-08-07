"""Old news and events cleanup job."""


async def run_retention_job() -> None:
    """Purge news articles older than 30 days."""
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_retention_job())
