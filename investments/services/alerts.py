import logging

from django.db import transaction

from investments.models import Notification, PriceAlert

from .history import fmt, to_decimal

logger = logging.getLogger("main")


def check_alerts(shares, triggered_at):
    """Fire active alerts whose condition is met by the new prices of `shares`."""
    prices = {s.id: to_decimal(s.last_price) for s in shares if s.last_price is not None}
    alerts = PriceAlert.objects.filter(
        triggered_at__isnull=True, item__share_id__in=prices
    ).select_related("item__share", "item__watchlist")

    created = []
    for alert in alerts:
        price = prices[alert.item.share_id]
        if not alert.is_met(price):
            continue
        with transaction.atomic():
            # Only the worker that flips triggered_at creates the notification
            if not PriceAlert.objects.filter(pk=alert.pk, triggered_at__isnull=True).update(
                triggered_at=triggered_at
            ):
                continue
            share = alert.item.share
            created.append(
                Notification.objects.create(
                    user=alert.item.watchlist.user,
                    alert=alert,
                    share=share,
                    price=price,
                    triggered_at=triggered_at,
                    message=(
                        f"{share.ticker}: цена {fmt(price)} {share.currency} "
                        f"({alert.get_condition_display()} {fmt(alert.target_price)})"
                    ),
                )
            )
    if created:
        logger.info(f"Created {len(created)} price alert notifications")
    return created
