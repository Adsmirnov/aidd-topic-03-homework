from dataclasses import dataclass, field
from decimal import Decimal

from investments.models import PortfolioOperation

from .history import to_decimal

ZERO = Decimal("0")


@dataclass
class Position:
    """A share in a portfolio, average cost method: a sale does not change the average price."""

    share: object
    quantity: int = 0
    cost: Decimal = ZERO  # what the current quantity cost (average price × quantity)
    realized: Decimal = ZERO  # profit/loss of the sales

    @property
    def avg_price(self):
        return self.cost / self.quantity if self.quantity else None

    @property
    def current_price(self):
        return to_decimal(self.share.last_price) if self.share.last_price is not None else None

    @property
    def market_value(self):
        if self.current_price is None:
            return None
        return self.current_price * self.quantity

    @property
    def unrealized(self):
        if self.market_value is None or not self.quantity:
            return None
        return self.market_value - self.cost

    @property
    def unrealized_percent(self):
        if self.unrealized is None or not self.cost:
            return None
        return self.unrealized / self.cost * 100

    def apply(self, side, quantity, price):
        if side == PortfolioOperation.BUY:
            self.cost += price * quantity
            self.quantity += quantity
        else:
            if quantity > self.quantity:
                raise ValueError(f"Нельзя продать {quantity}: в портфеле {self.quantity}")
            avg_price = self.avg_price
            self.realized += (price - avg_price) * quantity
            self.cost -= avg_price * quantity
            self.quantity -= quantity


@dataclass
class PortfolioSummary:
    positions: list = field(default_factory=list)
    invested: Decimal = ZERO
    market_value: Decimal = ZERO
    unrealized: Decimal = ZERO
    realized: Decimal = ZERO
    has_unpriced: bool = False

    @property
    def total(self):
        return self.unrealized + self.realized


def build_positions(operations):
    """Replay operations in time order → {share_id: Position}."""
    positions = {}
    for op in operations:
        position = positions.setdefault(op.share_id, Position(share=op.share))
        position.apply(op.side, op.quantity, op.price)
    return positions


def held_quantity(portfolio, share):
    position = build_positions(portfolio.operations.filter(share=share)).get(share.id)
    return position.quantity if position else 0


def summarize(portfolio):
    operations = portfolio.operations.select_related("share").order_by("executed_at", "id")
    positions = sorted(
        build_positions(operations).values(),
        key=lambda p: (p.quantity == 0, p.share.ticker),
    )
    summary = PortfolioSummary(positions=positions)
    for p in positions:
        summary.realized += p.realized
        if not p.quantity:
            continue
        summary.invested += p.cost
        if p.market_value is None:
            summary.has_unpriced = True
        else:
            summary.market_value += p.market_value
            summary.unrealized += p.unrealized
    return summary
