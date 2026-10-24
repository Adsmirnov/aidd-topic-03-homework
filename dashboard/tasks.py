from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data
from config.settings import logger


@app.task
def update_last_price():
    shares = Share.objects.all().iterator()

    for share in shares:
        try:
            last_price, _ = get_last_data(share)
            share.is_trend_high = share.last_price is None or last_price >= share.last_price
            share.last_price = last_price
            share.save(update_fields=("last_price", "is_trend_high", "updated_at"))
        except Exception:
            logger.exception("Failed to update price for share %s", share.pk)
