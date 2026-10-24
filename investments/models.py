from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from dashboard.models import Share

PRICE_DIGITS = dict(max_digits=18, decimal_places=6)
POSITIVE = [MinValueValidator(Decimal("0.000001"))]


class SharePrice(models.Model):
    """Цена акции в момент времени (история цен)"""

    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name="prices")
    price = models.DecimalField(**PRICE_DIGITS, verbose_name="Цена")
    recorded_at = models.DateTimeField(db_index=True, verbose_name="Время")

    class Meta:
        verbose_name = "Цена акции"
        verbose_name_plural = "История цен"
        ordering = ["recorded_at", "id"]
        indexes = [models.Index(fields=["share", "recorded_at"])]

    def __str__(self):
        return f"{self.share.ticker} {self.price} {self.recorded_at:%Y-%m-%d %H:%M}"


class Watchlist(models.Model):
    """Персональный список наблюдения"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlists"
    )
    name = models.CharField(max_length=100, verbose_name="Название")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Список наблюдения"
        verbose_name_plural = "Списки наблюдения"
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class WatchlistItem(models.Model):
    """Акция в списке наблюдения"""

    watchlist = models.ForeignKey(Watchlist, on_delete=models.CASCADE, related_name="items")
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name="+")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["share__ticker"]
        constraints = [
            models.UniqueConstraint(
                fields=["watchlist", "share"], name="unique_share_in_watchlist"
            )
        ]

    def __str__(self):
        return f"{self.watchlist}: {self.share.ticker}"


class PriceAlert(models.Model):
    """Целевой ценовой уровень для акции из списка наблюдения"""

    ABOVE = "above"
    BELOW = "below"
    CONDITIONS = [(ABOVE, "цена ≥ уровня"), (BELOW, "цена ≤ уровня")]

    item = models.ForeignKey(WatchlistItem, on_delete=models.CASCADE, related_name="alerts")
    condition = models.CharField(max_length=5, choices=CONDITIONS, verbose_name="Условие")
    target_price = models.DecimalField(
        **PRICE_DIGITS, validators=POSITIVE, verbose_name="Целевая цена"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Set when the condition is met; a triggered alert does not fire again
    triggered_at = models.DateTimeField(null=True, blank=True, verbose_name="Сработал")

    class Meta:
        ordering = ["target_price"]

    def __str__(self):
        return f"{self.item.share.ticker} {self.get_condition_display()} {self.target_price}"

    def is_met(self, price):
        if self.condition == self.ABOVE:
            return price >= self.target_price
        return price <= self.target_price


class Notification(models.Model):
    """Уведомление о срабатывании ценового уровня"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    alert = models.ForeignKey(PriceAlert, on_delete=models.CASCADE, related_name="notifications")
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name="+")
    message = models.CharField(max_length=255)
    price = models.DecimalField(**PRICE_DIGITS, verbose_name="Цена")
    triggered_at = models.DateTimeField(verbose_name="Время")
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-triggered_at", "-id"]
        constraints = [
            # One notification per triggering of an alert, even with parallel workers
            models.UniqueConstraint(
                fields=["alert", "triggered_at"], name="one_notification_per_trigger"
            )
        ]

    def __str__(self):
        return self.message


class Portfolio(models.Model):
    """Виртуальный инвестиционный портфель"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios"
    )
    name = models.CharField(max_length=100, verbose_name="Название")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Портфель"
        verbose_name_plural = "Портфели"
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class PortfolioOperation(models.Model):
    """Смоделированная покупка или продажа акции в портфеле (журнал не редактируется)"""

    BUY = "buy"
    SELL = "sell"
    SIDES = [(BUY, "Покупка"), (SELL, "Продажа")]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="operations")
    share = models.ForeignKey(Share, on_delete=models.PROTECT, related_name="+")
    side = models.CharField(max_length=4, choices=SIDES, verbose_name="Операция")
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="Количество"
    )
    price = models.DecimalField(**PRICE_DIGITS, validators=POSITIVE, verbose_name="Цена")
    executed_at = models.DateTimeField(default=timezone.now, verbose_name="Время")
    comment = models.CharField(max_length=255, blank=True, verbose_name="Комментарий")

    class Meta:
        ordering = ["executed_at", "id"]

    def __str__(self):
        return f"{self.get_side_display()} {self.share.ticker} × {self.quantity} по {self.price}"

    @property
    def amount(self):
        return self.price * self.quantity
