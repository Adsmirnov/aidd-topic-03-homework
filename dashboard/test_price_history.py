from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import PriceHistory, Share
from dashboard.services.price_history import record_price
from dashboard.tasks import update_last_price


class PriceHistoryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="history@example.com", email="history@example.com", password="test-pass"
        )
        self.share = Share.objects.create(
            figi="HISTORY-FIGI",
            isin="HISTORY-ISIN",
            name="History Company",
            ticker="HIST",
            currency="usd",
            uid="history-uid",
        )
        self.first_time = datetime(2026, 10, 1, tzinfo=timezone.utc)
        self.last_time = datetime(2026, 10, 11, tzinfo=timezone.utc)
        record_price(self.share, "100", self.first_time)
        record_price(self.share, "110", self.last_time)

    def test_history_filters_period_and_calculates_changes(self):
        response = self.client.get(
            reverse("dashboard:history:index"),
            {
                "share": self.share.pk,
                "start_date": "2026-10-01",
                "end_date": "2026-10-11",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["entries"]), 2)
        self.assertEqual(response.context["absolute_change"], Decimal("10.00000000"))
        self.assertEqual(response.context["percent_change"], Decimal("10"))
        self.assertContains(response, "plotly-graph-div")

    def test_history_rejects_inverted_date_range(self):
        response = self.client.get(
            reverse("dashboard:history:index"),
            {
                "share": self.share.pk,
                "start_date": "2026-10-11",
                "end_date": "2026-10-01",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Начало периода должно быть не позже его конца")

    def test_same_share_timestamp_is_deduplicated(self):
        record_price(self.share, "101", self.first_time)

        self.assertEqual(PriceHistory.objects.filter(share=self.share).count(), 2)
        self.assertEqual(
            PriceHistory.objects.get(share=self.share, observed_at=self.first_time).price,
            Decimal("100"),
        )

    @patch(
        "dashboard.tasks.get_last_data",
        return_value=(Decimal("111.25"), datetime(2026, 10, 24, tzinfo=timezone.utc)),
    )
    def test_quote_task_persists_price_history(self, get_last_data_mock):
        update_last_price()

        point = PriceHistory.objects.get(
            share=self.share,
            observed_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        self.assertEqual(point.price, Decimal("111.25"))
        get_last_data_mock.assert_called_once()

    def test_history_page_is_available_without_login(self):
        response = self.client.get(reverse("dashboard:history:index"))
        self.assertEqual(response.status_code, 200)
