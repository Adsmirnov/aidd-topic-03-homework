from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import OuterRef, Subquery
from django.utils import timezone

from investments.models import SharePrice


def to_decimal(value):
    """Share.last_price is a float; str() keeps the value as it is shown."""
    return Decimal(str(value))


def fmt(value):
    """Decimal without trailing zeros and without exponent: 100.000000 → '100'."""
    return format(value.normalize(), "f")


def record_prices(shares, recorded_at):
    """Save the current price of each share unless it equals the last saved one."""
    last_saved = dict(
        SharePrice.objects.filter(share__in=shares)
        .filter(
            id=Subquery(
                SharePrice.objects.filter(share=OuterRef("share"))
                .order_by("-recorded_at", "-id")
                .values("id")[:1]
            )
        )
        .values_list("share_id", "price")
    )
    new_prices = [
        SharePrice(share=share, price=to_decimal(share.last_price), recorded_at=recorded_at)
        for share in shares
        if share.last_price is not None
        and last_saved.get(share.id) != to_decimal(share.last_price)
    ]
    SharePrice.objects.bulk_create(new_prices)
    return new_prices


PERIODS = {
    "1d": ("1 день", timedelta(days=1)),
    "7d": ("7 дней", timedelta(days=7)),
    "30d": ("30 дней", timedelta(days=30)),
    "90d": ("90 дней", timedelta(days=90)),
    "365d": ("1 год", timedelta(days=365)),
    "all": ("Всё время", None),
}
DEFAULT_PERIOD = "30d"


def period_bounds(period=None, date_from=None, date_to=None, now=None):
    """(start, end) for a preset period or a custom date range; start None = no limit."""
    now = now or timezone.now()
    if date_from or date_to:
        tz = timezone.get_current_timezone()
        start = datetime.combine(date_from, time.min, tz) if date_from else None
        end = datetime.combine(date_to, time.max, tz) if date_to else now
        return start, end
    delta = PERIODS.get(period, PERIODS[DEFAULT_PERIOD])[1]
    return (now - delta if delta else None), now


@dataclass
class PeriodStats:
    start_price: Decimal
    end_price: Decimal
    change: Decimal
    change_percent: Decimal
    min_price: Decimal
    max_price: Decimal
    count: int


def get_history(share, start, end):
    """Records within the period plus the price in effect at its start (or None)."""
    records = share.prices.filter(recorded_at__lte=end)
    baseline = None
    if start is not None:
        baseline = records.filter(recorded_at__lt=start).last()
        records = records.filter(recorded_at__gte=start)
    return list(records), baseline


def period_stats(records, baseline=None):
    if not records:
        return None
    prices = [r.price for r in records]
    start_price = baseline.price if baseline else prices[0]
    end_price = prices[-1]
    change = end_price - start_price
    return PeriodStats(
        start_price=start_price,
        end_price=end_price,
        change=change,
        change_percent=(
            (change / start_price * 100).quantize(Decimal("0.01")) if start_price else None
        ),
        min_price=min(prices),
        max_price=max(prices),
        count=len(records),
    )
