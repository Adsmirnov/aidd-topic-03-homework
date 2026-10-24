from django.core.management.base import BaseCommand

from dashboard.models import Share
from dashboard.services.tinkoff_api import post


class Command(BaseCommand):
    help = "Add shares to DB"

    def handle(self, *args, **options):
        response = post(
            "InstrumentsService/Shares",
            {"instrumentStatus": "INSTRUMENT_STATUS_BASE"},
        )
        created_count = 0
        for instrument in response.get("instruments", []):
            _, created = Share.objects.get_or_create(
                figi=instrument["figi"],
                defaults={
                    "name": instrument["name"],
                    "isin": instrument["isin"],
                    "ticker": instrument["ticker"],
                    "currency": instrument["currency"],
                    "uid": instrument["uid"],
                },
            )
            created_count += created

        self.stdout.write(f"Created {created_count} shares.")


