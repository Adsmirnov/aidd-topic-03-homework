"""Regression tests for the defects listed in ANALYSIS.md (section 11)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from tinkoff.invest import Quotation

from dashboard.models import Share
from dashboard.tasks import update_last_price


def make_share(**kwargs):
    defaults = dict(
        figi="BBG000B9XRY4",
        isin="US0378331005",
        name="Apple",
        ticker="AAPL",
        currency="usd",
        uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
    )
    defaults.update(kwargs)
    return Share.objects.create(**defaults)


def fake_client(client):
    """Patch target for `Client(token)` used as a context manager."""
    context = MagicMock()
    context.__enter__.return_value = client
    return MagicMock(return_value=context)


class PriceUpdateTests(TestCase):
    def last_prices(self, *prices):
        return SimpleNamespace(
            last_prices=[
                SimpleNamespace(
                    figi=figi,
                    price=Quotation(units=units, nano=nano),
                    time=datetime(2026, 10, 24, tzinfo=timezone.utc),
                )
                for figi, units, nano in prices
            ]
        )

    def run_task(self, *prices):
        client = MagicMock()
        client.market_data.get_last_prices.return_value = self.last_prices(*prices)
        with patch("dashboard.services.tinkoff.Client", fake_client(client)):
            update_last_price()
        return client

    def test_fractional_part_of_price_is_kept(self):
        """Д-6: 172.64 must not become 172."""
        share = make_share()
        self.run_task((share.figi, 172, 640_000_000))
        share.refresh_from_db()
        self.assertAlmostEqual(share.last_price, 172.64)

    def test_updated_at_changes_when_price_is_updated(self):
        """Д-7: QuerySet.update() skipped auto_now."""
        share = make_share()
        old = share.updated_at
        self.run_task((share.figi, 10, 0))
        share.refresh_from_db()
        self.assertGreater(share.updated_at, old)

    def test_trend_rules(self):
        """ФТ-28: rise on >= previous price or when there was no price."""
        share = make_share()
        self.run_task((share.figi, 10, 0))
        share.refresh_from_db()
        self.assertTrue(share.is_trend_high)
        self.run_task((share.figi, 9, 500_000_000))
        share.refresh_from_db()
        self.assertFalse(share.is_trend_high)
        self.run_task((share.figi, 9, 500_000_000))
        share.refresh_from_db()
        self.assertTrue(share.is_trend_high)

    def test_prices_are_requested_in_one_call(self):
        """Д-8: one request for all shares instead of one per share."""
        first = make_share()
        second = make_share(figi="F2", ticker="T2", uid="u2", isin="I2")
        client = self.run_task((first.figi, 1, 0), (second.figi, 2, 0))
        self.assertEqual(client.market_data.get_last_prices.call_count, 1)
        second.refresh_from_db()
        self.assertEqual(second.last_price, 2)


class AddSharesTests(TestCase):
    def instrument(self, name):
        return SimpleNamespace(
            figi="BBG000B9XRY4",
            name=name,
            isin="US0378331005",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
        )

    def load(self, *instruments):
        client = MagicMock()
        client.instruments.shares.return_value = SimpleNamespace(
            instruments=list(instruments)
        )
        with patch(
            "dashboard.services.tinkoff.Client", fake_client(client)
        ):
            call_command("add_shares")

    def test_reload_updates_changed_share(self):
        """Д-9: a renamed share broke the load with IntegrityError."""
        self.load(self.instrument("Apple"))
        self.load(self.instrument("Apple Inc."))
        self.assertEqual(Share.objects.count(), 1)
        self.assertEqual(Share.objects.get().name, "Apple Inc.")


class ShareApiDefectTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("a@a.ru", "a@a.ru", "pw")

    def share_payload(self, n):
        return {
            "figi": f"FIGI{n}",
            "isin": f"ISIN{n}",
            "name": f"Company {n}",
            "ticker": f"T{n}",
            "currency": "rub",
        }

    def test_two_shares_without_uid_can_be_created(self):
        """Д-10: the second share without uid failed with 500."""
        self.client.force_authenticate(self.user)
        for n in (1, 2):
            response = self.client.post(
                "/api/v1/shares/", self.share_payload(n), format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_regex_search_is_400(self):
        """Д-13: an invalid regular expression gave 500."""
        response = self.client.get("/api/v1/shares/", {"search": "("})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_regex_search_still_works(self):
        make_share()
        response = self.client.get("/api/v1/shares/", {"search": "^App"})
        self.assertEqual(response.data["count"], 1)

    def test_guest_cannot_modify_shares(self):
        """Д-14: API allowed anonymous create/update/delete."""
        share = make_share()
        response = self.client.post(
            "/api/v1/shares/", self.share_payload(1), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(f"/api/v1/shares/{share.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_read_shares(self):
        make_share()
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ShareDetailDefectTests(TestCase):
    def test_missing_share_is_404(self):
        """Д-11: /999 gave 500."""
        response = self.client.get("/999")
        self.assertEqual(response.status_code, 404)

    def test_page_works_when_market_api_fails(self):
        """Д-12: an API error made the whole page fail."""
        share = make_share(last_price=10.5)
        broken = MagicMock(side_effect=RuntimeError("no network"))
        with patch("dashboard.services.tinkoff.Client", broken):
            response = self.client.get(f"/{share.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apple")
        self.assertContains(response, "График недоступен")

    def test_chart_uses_fractional_prices(self):
        """Д-6 for the chart."""
        share = make_share()
        candle = SimpleNamespace(
            time=datetime(2026, 10, 1, tzinfo=timezone.utc),
            close=Quotation(units=0, nano=34_500_000),
        )
        client = MagicMock()
        client.get_all_candles.return_value = [candle]
        with patch("dashboard.services.tinkoff.Client", fake_client(client)):
            response = self.client.get(f"/{share.id}")
        self.assertContains(response, "0.0345")
