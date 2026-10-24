import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dashboard.models import Share
from investments.models import SharePrice

DEMO_UID_PREFIX = "demo-"


class Command(BaseCommand):
    help = (
        "Fill the price history of DEMO shares (uid starts with 'demo-') with "
        "synthetic prices: a random walk with a fixed seed. Real shares are never touched."
    )

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=120)
        parser.add_argument("--per-day", type=int, default=4)
        parser.add_argument("--seed", type=int, default=42)

    @transaction.atomic
    def handle(self, *args, days, per_day, seed, **options):
        rng = random.Random(seed)
        shares = list(Share.objects.filter(uid__startswith=DEMO_UID_PREFIX))
        if not shares:
            self.stdout.write("No demo shares. Run: python manage.py loaddata demo_shares")
            return

        now = timezone.now().replace(microsecond=0)
        step = timedelta(days=1) / per_day
        for share in shares:
            SharePrice.objects.filter(share=share).delete()
            price = Decimal(str(share.last_price or rng.uniform(50, 500)))
            records = []
            for i in range(days * per_day, -1, -1):
                price = max(price * Decimal(str(1 + rng.gauss(0, 0.012))), Decimal("0.01"))
                records.append(
                    SharePrice(share=share, price=price.quantize(Decimal("0.01")),
                               recorded_at=now - step * i)
                )
            SharePrice.objects.bulk_create(records)
            share.is_trend_high = records[-1].price >= records[-2].price
            share.last_price = float(records[-1].price)
            share.updated_at = now
            share.save()
            self.stdout.write(f"{share.ticker}: {len(records)} demo prices")
