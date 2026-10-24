from config.celery import app
from dashboard.models import Share
from dashboard.services.alerts import evaluate_price_alerts
from dashboard.services.market_data import get_last_data
from dashboard.services.price_history import record_price
from dashboard.services.strategies import process_price_update
from config.settings import logger


@app.task
def update_last_price():
    shares = Share.objects.all().iterator()

    for share in shares:
        try:
            last_price, observed_at = get_last_data(share)
            share.is_trend_high = share.last_price is None or last_price >= share.last_price
            share.last_price = last_price
            share.save(update_fields=("last_price", "is_trend_high", "updated_at"))
            record_price(share, last_price, observed_at)
            evaluate_price_alerts(share, last_price)
            process_price_update(share, last_price, observed_at)
        except Exception:
            logger.exception("Failed to update price for share %s", share.pk)
