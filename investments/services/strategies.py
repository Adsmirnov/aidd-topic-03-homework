import logging
from dataclasses import dataclass
from decimal import Decimal

from django.db import IntegrityError, transaction

from investments.models import PortfolioOperation, Strategy, StrategyTrade

from .history import to_decimal

logger = logging.getLogger("main")

BUY, SELL = PortfolioOperation.BUY, PortfolioOperation.SELL
REASON_BUY = "цена ≤ уровня покупки"
REASON_SELL = "цена ≥ уровня продажи"
REASON_STOP = "стоп-лосс"


@dataclass
class Trade:
    side: str
    quantity: int
    price: Decimal
    executed_at: object
    reason: str


def decide(strategy, holding, price):
    """(side, reason) the strategy takes at `price`, or None. One position at a time."""
    if not holding:
        # No buying at or below the stop-loss: it would be sold on the next update
        above_stop = strategy.stop_price is None or price > strategy.stop_price
        if price <= strategy.buy_price and above_stop:
            return BUY, REASON_BUY
        return None
    if strategy.stop_price is not None and price <= strategy.stop_price:
        return SELL, REASON_STOP
    if price >= strategy.sell_price:
        return SELL, REASON_SELL
    return None


def simulate(strategy, prices, holding=False):
    """Apply the strategy to [(time, price), ...] in order; returns the trades."""
    trades = []
    for executed_at, price in prices:
        decision = decide(strategy, holding, price)
        if decision:
            side, reason = decision
            trades.append(Trade(side, strategy.quantity, price, executed_at, reason))
            holding = side == BUY
    return trades


@dataclass
class Performance:
    trades: int
    rounds: int
    winning_rounds: int
    realized: Decimal
    unrealized: Decimal
    capital: Decimal

    @property
    def total(self):
        return self.realized + self.unrealized

    @property
    def win_rate(self):
        return Decimal(self.winning_rounds * 100) / self.rounds if self.rounds else None

    @property
    def return_percent(self):
        """Total P/L relative to the capital the strategy needed (its largest buy)."""
        return self.total / self.capital * 100 if self.capital else None


def evaluate(trades, current_price):
    """Performance of a trade list; an open position is valued at `current_price`."""
    realized = Decimal(0)
    unrealized = Decimal(0)
    capital = Decimal(0)
    rounds = winning = 0
    open_buy = None
    for trade in trades:
        if trade.side == BUY:
            open_buy = trade
            capital = max(capital, trade.price * trade.quantity)
        elif open_buy is not None:
            profit = (trade.price - open_buy.price) * trade.quantity
            realized += profit
            rounds += 1
            winning += profit > 0
            open_buy = None
    if open_buy is not None and current_price is not None:
        unrealized = (current_price - open_buy.price) * open_buy.quantity
    return Performance(len(trades), rounds, winning, realized, unrealized, capital)


def is_holding(strategy):
    last = strategy.trades.order_by("-executed_at", "-id").first()
    return last is not None and last.side == BUY


def run_strategies(shares, executed_at):
    """Apply active strategies to the new prices and journal the virtual trades."""
    prices = {s.id: to_decimal(s.last_price) for s in shares if s.last_price is not None}
    created = []
    for strategy in Strategy.objects.filter(is_active=True, share_id__in=prices):
        price = prices[strategy.share_id]
        decision = decide(strategy, is_holding(strategy), price)
        if not decision:
            continue
        side, reason = decision
        try:
            with transaction.atomic():
                created.append(
                    StrategyTrade.objects.create(
                        strategy=strategy, side=side, quantity=strategy.quantity,
                        price=price, executed_at=executed_at, reason=reason,
                    )
                )
        except IntegrityError:
            # The same price update was already processed for this strategy
            continue
    if created:
        logger.info(f"Strategies made {len(created)} virtual trades")
    return created


def buy_and_hold_percent(prices):
    """Change from the first to the last price of the period, %."""
    if len(prices) < 2 or not prices[0][1]:
        return None
    first, last = prices[0][1], prices[-1][1]
    return (last - first) / first * 100
