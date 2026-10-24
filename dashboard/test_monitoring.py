from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import (
    AlertNotification,
    PriceAlert,
    Share,
    Watchlist,
    WatchlistEntry,
)
from dashboard.services.alerts import evaluate_price_alerts


class WatchlistTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner@example.com", email="owner@example.com", password="test-pass"
        )
        self.other_user = user_model.objects.create_user(
            username="other@example.com", email="other@example.com", password="test-pass"
        )
        self.share = Share.objects.create(
            figi="WATCH-FIGI",
            isin="WATCH-ISIN",
            name="Watched Company",
            ticker="WATCH",
            currency="usd",
            uid="watch-uid",
        )

    def test_monitoring_requires_login(self):
        response = self.client.get(reverse("dashboard:monitoring:index"))
        self.assertRedirects(
            response,
            f"{reverse('user:auth')}?next={reverse('dashboard:monitoring:index')}",
        )

    def test_owner_can_create_watchlist_entry_and_alert(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("dashboard:monitoring:create-watchlist"), {"name": "Core"}
        )
        self.assertRedirects(response, reverse("dashboard:monitoring:index"))
        watchlist = Watchlist.objects.get(owner=self.owner, name="Core")

        response = self.client.post(
            reverse("dashboard:monitoring:add-entry", args=[watchlist.pk]),
            {"share": self.share.pk},
        )
        entry = WatchlistEntry.objects.get(watchlist=watchlist, share=self.share)
        response = self.client.post(
            reverse("dashboard:monitoring:add-alert", args=[entry.pk]),
            {"direction": "above", "target_price": "125.50"},
        )
        self.assertRedirects(response, reverse("dashboard:monitoring:index"))
        self.assertEqual(entry.alerts.get().target_price, Decimal("125.50000000"))

    def test_user_cannot_access_another_users_watchlist(self):
        watchlist = Watchlist.objects.create(owner=self.owner, name="Private")
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("dashboard:monitoring:add-entry", args=[watchlist.pk]),
            {"share": self.share.pk},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(WatchlistEntry.objects.filter(watchlist=watchlist).exists())

    def test_price_alert_generates_only_one_notification(self):
        watchlist = Watchlist.objects.create(owner=self.owner, name="Alerts")
        entry = WatchlistEntry.objects.create(watchlist=watchlist, share=self.share)
        alert = PriceAlert.objects.create(
            entry=entry,
            direction=PriceAlert.Direction.ABOVE,
            target_price=Decimal("100.25"),
        )

        self.assertEqual(evaluate_price_alerts(self.share, Decimal("100.24")), [])
        first = evaluate_price_alerts(self.share, Decimal("100.25"))
        second = evaluate_price_alerts(self.share, Decimal("101.00"))

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertFalse(PriceAlert.objects.get(pk=alert.pk).is_active)
        self.assertEqual(AlertNotification.objects.filter(alert=alert).count(), 1)
        self.assertEqual(first[0].observed_price, Decimal("100.25"))

    def test_duplicate_watchlist_entry_is_idempotent(self):
        watchlist = Watchlist.objects.create(owner=self.owner, name="Once")
        WatchlistEntry.objects.get_or_create(watchlist=watchlist, share=self.share)
        WatchlistEntry.objects.get_or_create(watchlist=watchlist, share=self.share)
        self.assertEqual(WatchlistEntry.objects.filter(watchlist=watchlist).count(), 1)
