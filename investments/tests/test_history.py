from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase
from tinkoff.invest import Quotation

from dashboard.tasks import update_last_price
from investments.models import SharePrice
from investments.services.history import (
    get_history,
    period_bounds,
    period_stats,
    record_prices,
)

from .helpers import BASE_TIME, add_prices, make_share


class RecordPricesTests(TestCase):
    def test_saves_only_changed_prices(self):
        """НФТ-1."""
        share = make_share(last_price=100.5)
        record_prices([share], BASE_TIME)
        record_prices([share], BASE_TIME + timedelta(seconds=10))
        share.last_price = 101.25
        record_prices([share], BASE_TIME + timedelta(seconds=20))
        self.assertEqual(
            list(share.prices.values_list("price", flat=True)),
            [Decimal("100.5"), Decimal("101.25")],
        )

    def test_share_without_price_is_skipped(self):
        share = make_share(last_price=None)
        record_prices([share], BASE_TIME)
        self.assertFalse(SharePrice.objects.exists())

    def test_price_task_records_history(self):
        """НФТ-1 through the Celery task (T-Invest SDK client is mocked)."""
        share = make_share()
        client = MagicMock()
        client.market_data.get_last_prices.return_value = SimpleNamespace(
            last_prices=[SimpleNamespace(figi=share.figi, price=Quotation(units=12, nano=500_000_000))]
        )
        context = MagicMock()
        context.__enter__.return_value = client
        with patch("dashboard.services.tinkoff.Client", MagicMock(return_value=context)):
            update_last_price()
        self.assertEqual(share.prices.get().price, Decimal("12.5"))


class PeriodStatsTests(TestCase):
    def setUp(self):
        self.share = make_share()
        # days 0..4 → 100, 110, 90, 95, 120
        add_prices(self.share, 100, 110, 90, 95, 120)

    def stats_between(self, start, end):
        return period_stats(*get_history(self.share, start, end))

    def test_whole_history(self):
        """НФТ-3."""
        stats = self.stats_between(None, BASE_TIME + timedelta(days=10))
        self.assertEqual(stats.start_price, 100)
        self.assertEqual(stats.end_price, 120)
        self.assertEqual(stats.change, 20)
        self.assertEqual(stats.change_percent, Decimal("20.00"))
        self.assertEqual((stats.min_price, stats.max_price, stats.count), (90, 120, 5))

    def test_start_price_is_last_price_before_period(self):
        """НФТ-3: the period starts between records → price in effect at its start."""
        start = BASE_TIME + timedelta(days=1, hours=12)  # after 110, before 90
        stats = self.stats_between(start, BASE_TIME + timedelta(days=10))
        self.assertEqual(stats.start_price, 110)
        self.assertEqual(stats.change, 10)
        self.assertEqual(stats.change_percent, Decimal("9.09"))
        self.assertEqual(stats.count, 3)

    def test_empty_period(self):
        """НФТ-5."""
        self.assertIsNone(self.stats_between(BASE_TIME + timedelta(days=30), BASE_TIME + timedelta(days=40)))

    def test_custom_dates(self):
        start, end = period_bounds(date_from=date(2026, 10, 2), date_to=date(2026, 10, 3))
        records, baseline = get_history(self.share, start, end)
        self.assertEqual([r.price for r in records], [110, 90])
        self.assertEqual(baseline.price, 100)


class HistoryPageTests(TestCase):
    def test_page_shows_stats_and_chart(self):
        """НФТ-2, НФТ-4: the page is public."""
        share = make_share()
        add_prices(share, 100, 120)
        response = self.client.get(f"/history/{share.id}/", {"period": "all"})
        self.assertContains(response, "+20 rub")
        self.assertContains(response, "+20.00%")
        self.assertContains(response, "plotly")

    def test_empty_period_message(self):
        share = make_share()
        response = self.client.get(f"/history/{share.id}/", {"period": "1d"})
        self.assertContains(response, "сохранённых цен нет")

    def test_invalid_range_is_reported(self):
        share = make_share()
        response = self.client.get(
            f"/history/{share.id}/", {"date_from": "2026-10-05", "date_to": "2026-10-01"}
        )
        self.assertContains(response, "Дата начала позже даты окончания")

    def test_missing_share_is_404(self):
        self.assertEqual(self.client.get("/history/999/").status_code, 404)


class DemoPricesCommandTests(TestCase):
    def test_only_demo_shares_get_synthetic_prices(self):
        """НФТ-6."""
        demo = make_share("DEMO")
        demo.uid = "demo-x"
        demo.save()
        real = make_share("REAL")
        call_command("generate_demo_prices", days=2, per_day=2, stdout=StringIO())
        self.assertEqual(demo.prices.count(), 5)
        self.assertFalse(real.prices.exists())
        demo.refresh_from_db()
        self.assertEqual(Decimal(str(demo.last_price)), demo.prices.last().price)
