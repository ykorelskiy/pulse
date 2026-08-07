"""Order flow manager."""



class OrderFlowManager:
    """Manages order creation, payment state transitions, and delivery."""

    async def create_order(
        self, customer_tg: str, tier_id: str, description: str
    ) -> str:
        """Create new poster order.

        Returns:
            str: Order ID.
        """
        raise NotImplementedError
