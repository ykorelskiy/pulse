"""Commercial pricing calculator."""

from decimal import Decimal


class PricingCalculator:
    """Calculates order price using Decimal currency precision."""

    def get_tier_price(self, tier_id: str) -> Decimal:
        """Get exact tier price in Decimal currency.

        Returns:
            Decimal: Tier price.
        """
        raise NotImplementedError
