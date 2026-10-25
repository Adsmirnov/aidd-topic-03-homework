"""End-to-end checks of the T-Invest integration with a MOCKED API.

The SDK client is replaced with a fake that returns prepared data, so these
tests check our code around the API (requests we make, how responses are
stored and shown), NOT the real T-Invest API: no network calls are made and
token, TLS and the real response format are not verified.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from tinkoff.invest import Quotation

from dashboard.models import Share
from dashboard.services.tinkoff import tinkoff_client
from dashboard.tasks import update_last_price


def quotation(price):
    units = int(price)
    return Quotation(units=units, nano=round((price - units) * 1_000_000_000))


class FakeMarketApi:
    """Stands in for `Client(token)`: returns prepared prices, candles and shares."""

    def __init__(self, prices=None, candles=None, instruments=None):
        self.client = MagicMock()
        self.client.market_data.get_last_prices.side_effect = lambda figi: (
            SimpleNamespace(
                last_prices=[
                    SimpleNamespace(figi=f, price=quotation(prices[f]))
                    for f in figi
                    if f in (prices or {})
                ]
            )
        )
        self.client.get_all_candles.return_value = [
            SimpleNamespace(
                time=datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(days=i),
                close=quotation(close),
            )
            for i, close in enumerate(candles or [])
        ]
        self.client.instruments.shares.return_value = SimpleNamespace(
            instruments=instruments or []
        )

    def patch(self):
        context = MagicMock()
        context.__enter__.return_value = self.client
        return patch("dashboard.services.tinkoff.Client", MagicMock(return_value=context))


class MockedApiFlowTests(TestCase):
    fixtures = ["demo_shares"]

    def test_price_update_is_shown_in_list(self):
        """beat task → DB → list page: new prices and trend colours."""
        api = FakeMarketApi(
            prices={"BBG004730N88": 305.1, "BBG004731032": 6700.25, "BBG004730ZJ9": 0.0712}
        )
        with api.patch():
            update_last_price()

        sber, lkoh, vtbr = Share.objects.order_by("pk")
        self.assertEqual((sber.last_price, sber.is_trend_high), (305.1, True))
        self.assertEqual((lkoh.last_price, lkoh.is_trend_high), (6700.25, False))
        self.assertEqual((vtbr.last_price, vtbr.is_trend_high), (0.0712, True))

        response = self.client.get("/")
        self.assertContains(response, "305.1 rub")
        self.assertContains(response, "0.0712 rub")
        self.assertContains(response, "mediumseagreen")
        self.assertContains(response, "palevioletred")

    def test_unknown_figi_keeps_old_price(self):
        api = FakeMarketApi(prices={"BBG004730N88": 299.0})
        with api.patch():
            update_last_price()
        lkoh = Share.objects.get(ticker="LKOH")
        self.assertEqual(lkoh.last_price, 6820.5)

    def test_detail_page_shows_chart(self):
        api = FakeMarketApi(candles=[300.5, 301.0, 299.75])
        with api.patch():
            response = self.client.get("/9001")
        self.assertContains(response, "Сбер Банк")
        self.assertContains(response, "plotly")
        self.assertContains(response, "299.75")
        self.assertNotContains(response, "График недоступен")
        kwargs = api.client.get_all_candles.call_args.kwargs
        self.assertEqual(kwargs["figi"], "BBG004730N88")

    def test_add_shares_loads_new_and_updates_existing(self):
        instruments = [
            SimpleNamespace(
                figi="BBG004730N88",
                name="Сбер Банк",
                isin="RU0009029540",
                ticker="SBER",
                class_code="TQBR",
                currency="rub",
                uid="e6123145-9665-43e0-8413-cd61b8aa9b13",
            ),
            SimpleNamespace(
                figi="BBG004S681W1",
                name="МТС",
                isin="RU0007775219",
                ticker="MTSS",
                class_code="TQBR",
                currency="rub",
                uid="uid-mtss",
            ),
        ]
        with FakeMarketApi(instruments=instruments).patch():
            call_command("add_shares", stdout=MagicMock())
        self.assertEqual(Share.objects.count(), 4)
        self.assertEqual(Share.objects.get(ticker="SBER").name, "Сбер Банк")
        self.assertTrue(Share.objects.filter(ticker="MTSS").exists())


class ClientConfigurationTests(TestCase):
    @override_settings(TINKOFF_TOKEN="test-token")
    def test_client_uses_current_api_address(self):
        with patch("dashboard.services.tinkoff.Client") as client_class:
            tinkoff_client()
        client_class.assert_called_once_with(
            "test-token", target="invest-public-api.tbank.ru:443"
        )
