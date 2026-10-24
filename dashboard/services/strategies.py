from decimal import Decimal

from django.db import transaction

from dashboard.models import InvestmentStrategy, Share, StrategyTrade
from dashboard.services.portfolio import as_amount


@transaction.atomic
def process_price_update(share: Share, price: Decimal | float | str, market_at):
    market_price = as_amount(price)
    processed_trades = []
    strategies = InvestmentStrategy.objects.select_for_update().filter(
        share=share,
        is_active=True,
    )

    for strategy in strategies:
        if strategy.last_processed_at and strategy.last_processed_at >= market_at:
            continue

        if strategy.current_quantity == 0 and market_price <= strategy.buy_price:
            trade, created = StrategyTrade.objects.get_or_create(
                strategy=strategy,
                side=StrategyTrade.Side.BUY,
                market_at=market_at,
                defaults={
                    "market_price": market_price,
                    "quantity": strategy.quantity,
                },
            )
            if created:
                strategy.current_quantity = strategy.quantity
                strategy.average_buy_price = market_price
                processed_trades.append(trade)
        elif strategy.current_quantity > 0 and market_price >= strategy.sell_price:
            realized_pnl = as_amount(
                (market_price - strategy.average_buy_price) * strategy.current_quantity
            )
            trade, created = StrategyTrade.objects.get_or_create(
                strategy=strategy,
                side=StrategyTrade.Side.SELL,
                market_at=market_at,
                defaults={
                    "market_price": market_price,
                    "quantity": strategy.current_quantity,
                    "realized_pnl": realized_pnl,
                },
            )
            if created:
                strategy.realized_pnl += realized_pnl
                strategy.current_quantity = Decimal("0")
                strategy.average_buy_price = Decimal("0")
                processed_trades.append(trade)

        strategy.last_processed_at = market_at
        strategy.save(
            update_fields=(
                "current_quantity",
                "average_buy_price",
                "realized_pnl",
                "last_processed_at",
            )
        )

    return processed_trades
