from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from dashboard.models import AlertNotification, PriceAlert, Share


@transaction.atomic
def evaluate_price_alerts(share: Share, price: Decimal | float | str):
    observed_price = Decimal(str(price))
    notifications = []
    alerts = PriceAlert.objects.select_for_update().filter(
        entry__share=share,
        is_active=True,
    )

    for alert in alerts:
        if alert.direction == PriceAlert.Direction.ABOVE:
            triggered = observed_price >= alert.target_price
        else:
            triggered = observed_price <= alert.target_price

        if not triggered:
            continue

        updated = PriceAlert.objects.filter(pk=alert.pk, is_active=True).update(
            is_active=False,
            triggered_at=timezone.now(),
        )
        if updated:
            notification, created = AlertNotification.objects.get_or_create(
                alert=alert,
                defaults={"observed_price": observed_price},
            )
            if created:
                notifications.append(notification)

    return notifications
