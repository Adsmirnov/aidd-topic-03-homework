from decimal import Decimal

from django.test import TestCase

from investments.models import Portfolio, PortfolioOperation
from investments.services.portfolio import summarize

from .helpers import make_share, make_user


class PortfolioCalculationTests(TestCase):
    def setUp(self):
        self.portfolio = Portfolio.objects.create(user=make_user(), name="Тест")
        self.sber = make_share("SBER", last_price=130)

    def op(self, side, quantity, price, share=None):
        return PortfolioOperation.objects.create(
            portfolio=self.portfolio, share=share or self.sber, side=side,
            quantity=quantity, price=Decimal(str(price)),
        )

    def test_average_price_and_pnl(self):
        """НФТ-17, НФТ-18: average cost method."""
        self.op("buy", 10, 100)
        self.op("buy", 10, 120)  # avg = 110
        self.op("sell", 5, 140)  # realized = (140 - 110) * 5 = 150
        summary = summarize(self.portfolio)
        position = summary.positions[0]
        self.assertEqual(position.quantity, 15)
        self.assertEqual(position.avg_price, 110)
        self.assertEqual(position.cost, 1650)
        self.assertEqual(position.market_value, 1950)  # 15 × 130
        self.assertEqual(position.unrealized, 300)
        self.assertAlmostEqual(position.unrealized_percent, Decimal("18.1818"), places=4)
        self.assertEqual(position.realized, 150)
        self.assertEqual((summary.invested, summary.market_value), (1650, 1950))
        self.assertEqual((summary.unrealized, summary.realized, summary.total), (300, 150, 450))

    def test_closed_position_keeps_realized(self):
        self.op("buy", 2, 100)
        self.op("sell", 2, 90)
        summary = summarize(self.portfolio)
        self.assertEqual(summary.positions[0].quantity, 0)
        self.assertEqual(summary.realized, -20)
        self.assertEqual(summary.invested, 0)

    def test_position_without_price(self):
        """НФТ-18."""
        unpriced = make_share("NEW", last_price=None)
        self.op("buy", 1, 50, share=unpriced)
        self.op("buy", 1, 100)
        summary = summarize(self.portfolio)
        self.assertTrue(summary.has_unpriced)
        self.assertEqual(summary.market_value, 130)
        self.assertEqual(summary.invested, 150)


class PortfolioPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.share = make_share("SBER", last_price=101.5)
        self.client.post("/portfolios/", {"name": "Основной"})
        self.portfolio = Portfolio.objects.get()
        self.url = f"/portfolios/{self.portfolio.pk}/"

    def post_op(self, **data):
        return self.client.post(self.url, {"side": "buy", "ticker": "SBER", "quantity": 1, **data})

    def test_buy_uses_current_price_by_default(self):
        """НФТ-15."""
        self.post_op(quantity=3, comment="первая покупка")
        op = self.portfolio.operations.get()
        self.assertEqual((op.side, op.quantity, op.price), ("buy", 3, Decimal("101.5")))
        self.assertEqual(op.comment, "первая покупка")

    def test_cannot_sell_more_than_held(self):
        """НФТ-16."""
        self.post_op(quantity=2, price="100")
        response = self.post_op(side="sell", quantity=3)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Нельзя продать 3 SBER: в портфеле 2", status_code=400)
        self.assertEqual(self.portfolio.operations.count(), 1)

    def test_validation(self):
        self.assertEqual(self.post_op(quantity=0).status_code, 400)
        self.assertEqual(self.post_op(price="-5").status_code, 400)
        self.assertEqual(self.post_op(ticker="NOPE").status_code, 400)
        no_price = make_share("NEW", last_price=None)
        response = self.post_op(ticker=no_price.ticker)
        self.assertContains(response, "укажите цену", status_code=400)

    def test_page_shows_positions_and_history(self):
        """НФТ-17, НФТ-19."""
        self.post_op(quantity=2, price="100")
        self.post_op(side="sell", quantity=1, price="110")
        response = self.client.get(self.url)
        self.assertContains(response, "Продажа")
        self.assertContains(response, "Покупка")
        self.assertContains(response, "<td>10.00</td>", html=True)  # realized

    def test_other_users_portfolio_is_404(self):
        other = Portfolio.objects.create(user=make_user("o@test.ru"), name="Чужой")
        self.assertEqual(self.client.get(f"/portfolios/{other.pk}/").status_code, 404)

    def test_rename_and_delete(self):
        """НФТ-14."""
        self.client.post(f"{self.url}rename/", {"name": "Новый"})
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "Новый")
        self.client.post(f"{self.url}delete/")
        self.assertFalse(Portfolio.objects.exists())
