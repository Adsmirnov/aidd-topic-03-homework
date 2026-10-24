from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from investments.models import Notification, PriceAlert, Watchlist, WatchlistItem
from investments.services import on_prices_updated
from investments.services.alerts import check_alerts

from .helpers import BASE_TIME, make_share, make_user


class AlertServiceTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.share = make_share(last_price=100)
        watchlist = Watchlist.objects.create(user=self.user, name="Мой")
        self.item = WatchlistItem.objects.create(watchlist=watchlist, share=self.share)

    def alert(self, condition, target):
        return PriceAlert.objects.create(
            item=self.item, condition=condition, target_price=Decimal(str(target))
        )

    def update_price(self, price, minutes):
        self.share.last_price = price
        at = BASE_TIME + timedelta(minutes=minutes)
        on_prices_updated([self.share], at)
        return at

    def test_fires_when_condition_met(self):
        """НФТ-10."""
        above = self.alert(PriceAlert.ABOVE, 110)
        below = self.alert(PriceAlert.BELOW, 90)
        self.update_price(105, 1)
        self.assertFalse(Notification.objects.exists())
        at = self.update_price(110.5, 2)
        notification = Notification.objects.get()
        self.assertEqual(notification.alert, above)
        self.assertEqual(notification.price, Decimal("110.5"))
        self.assertEqual(notification.user, self.user)
        self.assertIn("SBER", notification.message)
        above.refresh_from_db()
        self.assertEqual(above.triggered_at, at)
        below.refresh_from_db()
        self.assertIsNone(below.triggered_at)

    def test_no_duplicates_for_same_event(self):
        """НФТ-11: price stays above the level for many updates → one notification."""
        self.alert(PriceAlert.ABOVE, 110)
        for minute, price in enumerate([111, 112, 115, 111, 120], start=1):
            self.update_price(price, minute)
        self.assertEqual(Notification.objects.count(), 1)

    def test_repeated_check_of_same_prices(self):
        """НФТ-11: the same batch processed twice (e.g. a retried task)."""
        self.alert(PriceAlert.BELOW, 100)
        check_alerts([self.share], BASE_TIME)
        check_alerts([self.share], BASE_TIME)
        self.assertEqual(Notification.objects.count(), 1)

    def test_database_rejects_second_notification_for_one_trigger(self):
        """НФТ-11: the unique constraint is the last line of defence."""
        alert = self.alert(PriceAlert.BELOW, 100)
        check_alerts([self.share], BASE_TIME)
        with self.assertRaises(IntegrityError):
            Notification.objects.create(
                user=self.user, alert=alert, share=self.share, message="dup",
                price=100, triggered_at=BASE_TIME,
            )

    def test_rearmed_alert_fires_again(self):
        """НФТ-12."""
        alert = self.alert(PriceAlert.ABOVE, 110)
        self.update_price(111, 1)
        alert.triggered_at = None
        alert.save()
        self.update_price(112, 2)
        self.assertEqual(Notification.objects.count(), 2)


class WatchlistPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.share = make_share(last_price=100)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get("/watchlists/")
        self.assertRedirects(response, "/user/login/?next=/watchlists/")

    def test_create_add_share_and_alert(self):
        """НФТ-7, НФТ-8, НФТ-9."""
        response = self.client.post("/watchlists/", {"name": "Банки"})
        watchlist = Watchlist.objects.get()
        self.assertRedirects(response, f"/watchlists/{watchlist.pk}/")

        self.client.post(f"/watchlists/{watchlist.pk}/", {"ticker": "sber"})
        item = watchlist.items.get()
        self.assertEqual(item.share, self.share)

        response = self.client.post(f"/watchlists/{watchlist.pk}/", {"ticker": "SBER"})
        self.assertContains(response, "уже есть в списке")
        response = self.client.post(f"/watchlists/{watchlist.pk}/", {"ticker": "NOPE"})
        self.assertContains(response, "нет в справочнике")

        self.client.post(
            f"/watchlists/items/{item.pk}/alerts/", {"condition": "below", "target_price": "95.5"}
        )
        self.assertEqual(item.alerts.get().target_price, Decimal("95.5"))
        response = self.client.post(
            f"/watchlists/items/{item.pk}/alerts/", {"condition": "below", "target_price": "-1"}
        )
        self.assertEqual(response.status_code, 400)

        self.client.post(f"/watchlists/{watchlist.pk}/rename/", {"name": "Банки РФ"})
        watchlist.refresh_from_db()
        self.assertEqual(watchlist.name, "Банки РФ")

    def test_other_users_watchlist_is_404(self):
        other = Watchlist.objects.create(user=make_user("other@test.ru"), name="Чужой")
        self.assertEqual(self.client.get(f"/watchlists/{other.pk}/").status_code, 404)
        self.assertEqual(self.client.post(f"/watchlists/{other.pk}/delete/").status_code, 404)
        self.assertTrue(Watchlist.objects.filter(pk=other.pk).exists())

    def test_unread_counter_and_mark_read(self):
        """НФТ-13."""
        watchlist = Watchlist.objects.create(user=self.user, name="Мой")
        item = WatchlistItem.objects.create(watchlist=watchlist, share=self.share)
        PriceAlert.objects.create(item=item, condition="below", target_price=100)
        check_alerts([self.share], BASE_TIME)
        response = self.client.get("/")
        self.assertContains(response, '<span class="badge bg-danger">1</span>', html=True)
        self.client.post("/notifications/read/")
        response = self.client.get("/notifications/")
        self.assertNotContains(response, "bg-danger")
        self.assertContains(response, "SBER: цена 100 rub")
