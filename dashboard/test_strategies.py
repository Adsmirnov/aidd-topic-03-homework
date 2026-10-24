from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import InvestmentStrategy, Share, StrategyTrade
from dashboard.services.strategies import process_price_update


class InvestmentStrategyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="strategy@example.com", email="strategy@example.com", password="test-pass"
        )
        self.other_user = user_model.objects.create_user(
            username="other-strategy@example.com",
            email="other-strategy@example.com",
            password="test-pass",
        )
        self.share = Share.objects.create(
            figi="STRATEGY-FIGI",
            isin="STRATEGY-ISIN",
            name="Strategy Company",
            ticker="STRAT",
            currency="usd",
            uid="strategy-uid",
        )
        self.strategy = InvestmentStrategy.objects.create(
            owner=self.owner,
            share=self.share,
            name="Buy low sell high",
            buy_price=Decimal("90"),
            sell_price=Decimal("110"),
            quantity=Decimal("2"),
        )
        self.market_at = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)

    def test_strategy_buys_and_sells_once_at_thresholds(self):
        self.assertEqual(process_price_update(self.share, "95", self.market_at), [])
        buy_trades = process_price_update(self.share, "90", self.market_at + timedelta(minutes=1))
        duplicate_buy = process_price_update(self.share, "90", self.market_at + timedelta(minutes=1))

        self.assertEqual(len(buy_trades), 1)
        self.assertEqual(buy_trades[0].side, StrategyTrade.Side.BUY)
        self.assertEqual(duplicate_buy, [])
        self.strategy.refresh_from_db()
        self.assertEqual(self.strategy.current_quantity, Decimal("2"))

        sell_trades = process_price_update(self.share, "110", self.market_at + timedelta(minutes=2))
        self.assertEqual(len(sell_trades), 1)
        self.assertEqual(sell_trades[0].side, StrategyTrade.Side.SELL)
        self.assertEqual(sell_trades[0].realized_pnl, Decimal("40.00000000"))
        self.strategy.refresh_from_db()
        self.assertEqual(self.strategy.current_quantity, Decimal("0"))
        self.assertEqual(self.strategy.realized_pnl, Decimal("40.00000000"))
        self.assertEqual(self.strategy.trades.count(), 2)

    def test_strategies_page_and_owner_scope(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard:strategies:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buy low sell high")

        self.client.force_login(self.other_user)
        response = self.client.get(reverse("dashboard:strategies:index"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Buy low sell high")

    def test_owner_can_pause_strategy(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("dashboard:strategies:toggle", args=[self.strategy.pk])
        )

        self.assertRedirects(response, reverse("dashboard:strategies:index"))
        self.strategy.refresh_from_db()
        self.assertFalse(self.strategy.is_active)
        self.assertEqual(
            process_price_update(self.share, "80", self.market_at), []
        )
        self.assertEqual(self.strategy.trades.count(), 0)
