from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dashboard.forms import PortfolioForm, PortfolioTransactionForm
from dashboard.models import Portfolio, PortfolioTransaction
from dashboard.services.portfolio import as_amount, execute_transaction


@login_required(login_url="user:auth")
def portfolios(request):
    owned_portfolios = Portfolio.objects.filter(owner=request.user).prefetch_related(
        "positions__share", "transactions__share"
    )
    portfolio_rows = []
    for portfolio in owned_portfolios:
        position_rows = []
        market_value = Decimal("0")
        cost_basis = Decimal("0")
        for position in portfolio.positions.all():
            last_price = (
                Decimal(str(position.share.last_price))
                if position.share.last_price is not None
                else None
            )
            current_value = as_amount(position.quantity * last_price) if last_price else Decimal("0")
            position_cost = as_amount(position.quantity * position.average_price)
            position_rows.append(
                {
                    "position": position,
                    "last_price": last_price,
                    "market_value": current_value,
                    "unrealized_pnl": as_amount(current_value - position_cost),
                }
            )
            market_value += current_value
            cost_basis += position_cost
        portfolio_rows.append(
            {
                "portfolio": portfolio,
                "positions": position_rows,
                "market_value": as_amount(market_value),
                "unrealized_pnl": as_amount(market_value - cost_basis),
                "transaction_form": PortfolioTransactionForm(),
            }
        )

    return render(
        request,
        "dashboard/portfolios.html",
        {"portfolio_rows": portfolio_rows, "portfolio_form": PortfolioForm()},
    )


@login_required(login_url="user:auth")
@require_POST
def create_portfolio(request):
    form = PortfolioForm(request.POST)
    if form.is_valid():
        portfolio = form.save(commit=False)
        portfolio.owner = request.user
        portfolio.save()
        messages.success(request, "Портфель создан.")
    else:
        messages.error(request, form.errors.as_text())
    return redirect("dashboard:portfolio-list")


@login_required(login_url="user:auth")
@require_POST
def record_transaction(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, pk=portfolio_id, owner=request.user)
    form = PortfolioTransactionForm(request.POST)
    if form.is_valid():
        try:
            execute_transaction(
                portfolio=portfolio,
                share=form.cleaned_data["share"],
                side=form.cleaned_data["side"],
                quantity=form.cleaned_data["quantity"],
                unit_price=form.cleaned_data["unit_price"],
            )
            messages.success(request, "Операция записана.")
        except ValueError as error:
            messages.error(request, str(error))
    else:
        messages.error(request, form.errors.as_text())
    return redirect("dashboard:portfolio-list")
