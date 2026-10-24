from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

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
