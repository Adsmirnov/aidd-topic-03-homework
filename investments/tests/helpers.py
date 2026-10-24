from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model

from dashboard.models import Share
from investments.models import SharePrice

BASE_TIME = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def make_share(ticker="SBER", last_price=None, **kwargs):
    return Share.objects.create(
        figi=f"FIGI-{ticker}",
        isin=f"ISIN-{ticker}",
        name=f"Company {ticker}",
        ticker=ticker,
        currency="rub",
        uid=f"uid-{ticker}",
        last_price=last_price,
        **kwargs,
    )


def make_user(email="user@test.ru"):
    return get_user_model().objects.create_user(email, email, "pw")


def add_prices(share, *prices, start=BASE_TIME, step=timedelta(days=1)):
    return [
        SharePrice.objects.create(share=share, price=Decimal(str(p)), recorded_at=start + step * i)
        for i, p in enumerate(prices)
    ]
