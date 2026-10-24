import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# Interval of the price refresh, seconds (all prices are fetched in one request)
PRICE_UPDATE_INTERVAL = float(os.getenv("PRICE_UPDATE_INTERVAL", "10"))

app.conf.beat_schedule = {
    "update-last-prices": {
        "task": "dashboard.tasks.update_last_price",
        "schedule": PRICE_UPDATE_INTERVAL,
    },
}
