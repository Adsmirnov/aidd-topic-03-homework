from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import (
    Portfolio,
    PortfolioPosition,
    PortfolioTransaction,
    Share,
)
from dashboard.services.portfolio import execute_transaction


class PortfolioTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="portfolio@example.com",
            email="portfolio@example.com",
            password="test-pass",
        )
        self.other_user = user_model.objects.create_user(
            username="other-portfolio@example.com",
            email="other-portfolio@example.com",
            password="test-pass",
        )
        self.share = Share.objects.create(
            figi="PORTFOLIO-FIGI",
            isin="PORTFOLIO-ISIN",
            name="Portfolio Company",
            ticker="PORT",
            currency="usd",
            uid="portfolio-uid",
            last_price=Decimal("25"),
        )
        self.portfolio = Portfolio.objects.create(owner=self.owner, name="Long term")

    def test_buy_sell_updates_average_cost_and_realized_profit(self):
        execute_transaction(
            self.portfolio, self.share, PortfolioTransaction.Side.BUY, "2", "10"
        )
        execute_transaction(
            self.portfolio, self.share, PortfolioTransaction.Side.BUY, "3", "20"
        )

        position = PortfolioPosition.objects.get(portfolio=self.portfolio, share=self.share)
        self.assertEqual(position.quantity, Decimal("5.00000000"))
        self.assertEqual(position.average_price, Decimal("16.00000000"))

        sale = execute_transaction(
            self.portfolio, self.share, PortfolioTransaction.Side.SELL, "2", "25"
        )
        position.refresh_from_db()
        self.assertEqual(position.quantity, Decimal("3.00000000"))
        self.assertEqual(position.average_price, Decimal("16.00000000"))
        self.assertEqual(sale.realized_pnl, Decimal("18.00000000"))

    def test_oversell_is_rejected_without_creating_transaction(self):
        execute_transaction(
            self.portfolio, self.share, PortfolioTransaction.Side.BUY, "1", "10"
        )

        with self.assertRaisesMessage(ValueError, "Нельзя продать больше"):
            execute_transaction(
                self.portfolio, self.share, PortfolioTransaction.Side.SELL, "2", "12"
            )

        self.assertEqual(self.portfolio.transactions.count(), 1)
        self.assertEqual(
            PortfolioPosition.objects.get(portfolio=self.portfolio).quantity,
            Decimal("1.00000000"),
        )

    def test_portfolio_page_shows_position_value_and_profit(self):
        execute_transaction(
            self.portfolio, self.share, PortfolioTransaction.Side.BUY, "2", "10"
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse("dashboard:portfolios:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "50.00000000")
        self.assertContains(response, "30.00000000")
        self.assertContains(response, "История операций")

    def test_user_cannot_submit_transaction_to_another_portfolio(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("dashboard:portfolios:transaction", args=[self.portfolio.pk]),
            {
                "share": self.share.pk,
                "side": "buy",
                "quantity": "1",
                "unit_price": "10",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.portfolio.transactions.count(), 0)
