from datetime import timedelta
from decimal import Decimal

from django.test import TestCase

from investments.models import Strategy, StrategyTrade
from investments.services import on_prices_updated
from investments.services.strategies import (
    REASON_BUY,
    REASON_SELL,
    REASON_STOP,
    buy_and_hold_percent,
    evaluate,
    run_strategies,
    simulate,
)

from .helpers import BASE_TIME, add_prices, make_share, make_user

D = Decimal


def make_strategy(share, user=None, **kwargs):
    params = dict(name="Тест", buy_price=D(100), sell_price=D(120), stop_price=D(90), quantity=10)
    params.update(kwargs)
    return Strategy.objects.create(user=user or make_user(), share=share, **params)


def prices(*values):
    return [(BASE_TIME + timedelta(days=i), D(str(v))) for i, v in enumerate(values)]


class EngineTests(TestCase):
    def setUp(self):
        self.strategy = make_strategy(make_share())

    def test_buy_sell_cycle(self):
        """НФТ-20: buy at ≤ buy level, sell all at ≥ sell level, one position at a time."""
        trades = simulate(self.strategy, prices(105, 99, 95, 110, 121, 125, 98))
        self.assertEqual(
            [(t.side, t.price, t.reason) for t in trades],
            [("buy", 99, REASON_BUY), ("sell", 121, REASON_SELL), ("buy", 98, REASON_BUY)],
        )

    def test_stop_loss(self):
        trades = simulate(self.strategy, prices(100, 95, 89))
        self.assertEqual([(t.side, t.reason) for t in trades], [("buy", REASON_BUY), ("sell", REASON_STOP)])

    def test_performance(self):
        """НФТ-22."""
        trades = simulate(self.strategy, prices(99, 121, 98, 89, 100))
        # rounds: 99→121 (+220), 98→89 stop (-90); open: buy 100, valued at 110 → +100
        performance = evaluate(trades, D(110))
        self.assertEqual((performance.trades, performance.rounds, performance.winning_rounds), (5, 2, 1))
        self.assertEqual(performance.realized, 130)
        self.assertEqual(performance.unrealized, 100)
        self.assertEqual(performance.total, 230)
        self.assertEqual(performance.capital, 1000)
        self.assertEqual(performance.return_percent, 23)
        self.assertEqual(performance.win_rate, 50)

    def test_buy_and_hold(self):
        self.assertEqual(buy_and_hold_percent(prices(100, 90, 125)), 25)
        self.assertIsNone(buy_and_hold_percent(prices(100)))

    def test_levels_validation(self):
        strategy = Strategy(buy_price=D(120), sell_price=D(100), quantity=1)
        with self.assertRaisesMessage(Exception, "ниже уровня продажи"):
            strategy.clean()


class LiveRunTests(TestCase):
    def setUp(self):
        self.share = make_share(last_price=None)
        self.strategy = make_strategy(self.share)

    def tick(self, price, minutes):
        self.share.last_price = price
        on_prices_updated([self.share], BASE_TIME + timedelta(minutes=minutes))

    def test_trades_are_journaled_automatically(self):
        """НФТ-21."""
        for minute, price in enumerate([105, 99.5, 98, 121, 130], start=1):
            self.tick(price, minute)
        trades = list(self.strategy.trades.all())
        self.assertEqual(
            [(t.side, t.price) for t in trades], [("buy", D("99.5")), ("sell", D("121"))]
        )

    def test_inactive_strategy_does_nothing(self):
        self.strategy.is_active = False
        self.strategy.save()
        self.tick(50, 1)
        self.assertFalse(StrategyTrade.objects.exists())

    def test_same_update_processed_twice(self):
        self.share.last_price = 99
        run_strategies([self.share], BASE_TIME)
        self.share.last_price = 125  # would sell, but it is the same price update
        run_strategies([self.share], BASE_TIME)
        self.assertEqual(StrategyTrade.objects.count(), 1)


class StrategyPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.share = make_share(last_price=110)

    def create(self, **data):
        payload = dict(name="Коридор", ticker="sber", buy_price="100", sell_price="120",
                       stop_price="", quantity="5", is_active="on")
        payload.update(data)
        return self.client.post("/strategies/", payload)

    def test_create_and_edit(self):
        """НФТ-20."""
        self.create()
        strategy = Strategy.objects.get()
        self.assertEqual((strategy.share, strategy.quantity, strategy.stop_price), (self.share, 5, None))
        self.client.post(f"/strategies/{strategy.pk}/", dict(
            name="Коридор 2", ticker="SBER", buy_price="95", sell_price="130", quantity="1"))
        strategy.refresh_from_db()
        self.assertEqual((strategy.name, strategy.buy_price, strategy.is_active), ("Коридор 2", 95, False))

    def test_invalid_levels(self):
        response = self.create(buy_price="130")
        self.assertContains(response, "ниже уровня продажи", status_code=400)
        response = self.create(stop_price="105")
        self.assertContains(response, "Стоп-лосс должен быть ниже", status_code=400)
        self.assertFalse(Strategy.objects.exists())

    def test_backtest_on_history(self):
        """НФТ-23: backtest uses stored prices and is not journaled."""
        self.create()
        strategy = Strategy.objects.get()
        add_prices(self.share, 110, 99, 105, 121, 115)
        response = self.client.get(f"/strategies/{strategy.pk}/", {"backtest": 1, "period": "all"})
        self.assertContains(response, "Цен в периоде: 5")
        self.assertContains(response, "«купить в начале и держать»: <b>4.55%</b>")
        self.assertEqual(len(response.context["backtest"]["trades"]), 2)
        self.assertEqual(response.context["backtest"]["performance"].realized, 110)
        self.assertFalse(StrategyTrade.objects.exists())

    def test_toggle_delete_and_ownership(self):
        self.create()
        strategy = Strategy.objects.get()
        self.client.post(f"/strategies/{strategy.pk}/toggle/")
        strategy.refresh_from_db()
        self.assertFalse(strategy.is_active)
        other = make_strategy(self.share, user=make_user("o@test.ru"))
        self.assertEqual(self.client.get(f"/strategies/{other.pk}/").status_code, 404)
        self.client.post(f"/strategies/{strategy.pk}/delete/")
        self.assertEqual(Strategy.objects.count(), 1)
