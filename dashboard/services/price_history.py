from decimal import Decimal

from dashboard.models import PriceHistory, Share


def record_price(share: Share, price: Decimal | float | str, observed_at):
    value = Decimal(str(price))
    if value <= 0:
        return None, False
    return PriceHistory.objects.get_or_create(
        share=share,
        observed_at=observed_at,
        defaults={"price": value},
    )
