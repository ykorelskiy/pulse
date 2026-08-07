"""Telegram bot main entrypoint."""


async def start_bot() -> None:
    """Start aiogram Telegram bot polling/webhook loop."""
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    asyncio.run(start_bot())
