from django.core.management.base import BaseCommand

from dashboard.models import Share
from dashboard.services.tinkoff import tinkoff_client


class Command(BaseCommand):
    help = "Add shares to DB"

    def handle(self, *args, **options):
        with tinkoff_client() as client:
            shares = client.instruments.shares()
            for share in shares.instruments:
                Share.objects.update_or_create(
                    figi=share.figi,
                    defaults=dict(
                        name=share.name,
                        isin=share.isin,
                        ticker=share.ticker,
                        currency=share.currency,
                        uid=share.uid,
                    ),
                )
        self.stdout.write(f"Loaded {len(shares.instruments)} shares")
