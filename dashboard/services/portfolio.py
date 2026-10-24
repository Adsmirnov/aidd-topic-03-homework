from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from dashboard.models import Portfolio, PortfolioPosition, PortfolioTransaction, Share


AMOUNT_STEP = Decimal("0.00000001")


def as_amount(value):
    return Decimal(str(value)).quantize(AMOUNT_STEP, rounding=ROUND_HALF_UP)


@transaction.atomic
def execute_transaction(
    portfolio: Portfolio,
    share: Share,
    side: str,
    quantity: Decimal | str,
    unit_price: Decimal | str,
) -> PortfolioTransaction:
    quantity = as_amount(quantity)
    unit_price = as_amount(unit_price)
    if quantity <= 0 or unit_price <= 0:
        raise ValueError("Количество и цена должны быть больше нуля.")

    locked_portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
    position, _ = PortfolioPosition.objects.get_or_create(
        portfolio=locked_portfolio,
        share=share,
    )
    position = PortfolioPosition.objects.select_for_update().get(pk=position.pk)

    realized_pnl = Decimal("0")
    if side == PortfolioTransaction.Side.BUY:
        new_quantity = position.quantity + quantity
        position.average_price = as_amount(
            (position.quantity * position.average_price + quantity * unit_price)
            / new_quantity
        )
        position.quantity = new_quantity
    elif side == PortfolioTransaction.Side.SELL:
        if quantity > position.quantity:
            raise ValueError("Нельзя продать больше акций, чем есть в портфеле.")
        realized_pnl = as_amount((unit_price - position.average_price) * quantity)
        position.quantity -= quantity
        if position.quantity == 0:
            position.average_price = Decimal("0")
    else:
        raise ValueError("Неизвестный тип операции.")

    position.save(update_fields=("quantity", "average_price", "updated_at"))
    return PortfolioTransaction.objects.create(
        portfolio=locked_portfolio,
        share=share,
        side=side,
        quantity=quantity,
        unit_price=unit_price,
        total_value=as_amount(quantity * unit_price),
        realized_pnl=realized_pnl,
    )
