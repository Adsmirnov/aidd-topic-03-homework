from django.db import models
from django.conf import settings


class Share(models.Model):
    """Акция"""

    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.FloatField(blank=True, null=True, verbose_name="Текущая цена")
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"


class Watchlist(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlists"
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("owner", "name"), name="uniq_watchlist_owner_name")
        ]
        ordering = ("name",)

    def __str__(self):
        return self.name


class WatchlistEntry(models.Model):
    watchlist = models.ForeignKey(
        Watchlist, on_delete=models.CASCADE, related_name="entries"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="watchlist_entries"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("watchlist", "share"), name="uniq_watchlist_share"
            )
        ]
        ordering = ("share__name",)


class PriceAlert(models.Model):
    class Direction(models.TextChoices):
        ABOVE = "above", "Выше цели"
        BELOW = "below", "Ниже цели"

    entry = models.ForeignKey(
        WatchlistEntry, on_delete=models.CASCADE, related_name="alerts"
    )
    direction = models.CharField(max_length=5, choices=Direction.choices)
    target_price = models.DecimalField(max_digits=20, decimal_places=8)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    triggered_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("entry", "direction", "target_price"),
                name="uniq_alert_target_per_entry",
            )
        ]
        ordering = ("target_price",)


class AlertNotification(models.Model):
    alert = models.OneToOneField(
        PriceAlert, on_delete=models.CASCADE, related_name="notification"
    )
    observed_price = models.DecimalField(max_digits=20, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)
