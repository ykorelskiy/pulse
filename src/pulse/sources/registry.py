"""Source registry loader."""

from pulse.sources.base import BaseSourceAdapter


class SourceRegistry:
    """Registry managing active news source adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseSourceAdapter] = {}

    def register(self, adapter: BaseSourceAdapter) -> None:
        """Register a new source adapter instance."""
        raise NotImplementedError

    def get_all(self) -> list[BaseSourceAdapter]:
        """Get all registered source adapters."""
        raise NotImplementedError
