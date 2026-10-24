from django.utils import timezone

from config.celery import app
from config.settings import logger
from dashboard.models import Share
from dashboard.services.market_data import get_last_prices


@app.task
def update_last_price():
    shares = list(Share.objects.all())
    if not shares:
        return

    try:
        prices = get_last_prices([share.figi for share in shares])
    except Exception as e:
        logger.error(f"Failed to get last prices: {e}")
        return

    updated_at = timezone.now()
    changed = []
    for share in shares:
        last_price = prices.get(share.figi)
        if last_price is None:
            continue
        # The price is "rising" unless it went down (or there was no price yet)
        share.is_trend_high = share.last_price is None or last_price >= share.last_price
        share.last_price = last_price
        # bulk_update() does not apply auto_now, so the time is set explicitly
        share.updated_at = updated_at
        changed.append(share)

    Share.objects.bulk_update(changed, ["last_price", "is_trend_high", "updated_at"])
