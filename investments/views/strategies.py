from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from investments.charts import line_chart
from investments.forms import HistoryPeriodForm, StrategyForm
from investments.models import Strategy
from investments.services import strategies as engine
from investments.services.history import get_history, period_bounds, to_decimal


def current_price(strategy):
    last_price = strategy.share.last_price
    return to_decimal(last_price) if last_price is not None else None


@login_required
def strategy_list(request):
    """Стратегии пользователя с показателями и создание новой"""
    form = StrategyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.instance.user = request.user
        strategy = form.save()
        return redirect("investments:strategy", pk=strategy.pk)
    rows = [
        (s, engine.evaluate(list(s.trades.all()), current_price(s)))
        for s in request.user.strategies.select_related("share")
    ]
    return render(
        request,
        "investments/strategies.html",
        {"rows": rows, "form": form},
        status=400 if form.errors else 200,
    )


@login_required
def strategy_detail(request, pk):
    """Параметры, показатели, журнал сделок и бэктест на истории цен"""
    strategy = get_object_or_404(Strategy.objects.select_related("share"), pk=pk, user=request.user)
    form = StrategyForm(request.POST or None, instance=strategy)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("investments:strategy", pk=pk)

    trades = list(strategy.trades.all())
    context = {
        "strategy": strategy,
        "form": form,
        "trades": trades[::-1],
        "performance": engine.evaluate(trades, current_price(strategy)),
        "holding": engine.is_holding(strategy),
        "period_form": HistoryPeriodForm(request.GET or None),
    }

    if "backtest" in request.GET and context["period_form"].is_valid():
        params = context["period_form"].cleaned_data
        start, end = period_bounds(
            params.get("period"), params.get("date_from"), params.get("date_to")
        )
        records, _ = get_history(strategy.share, start, end)
        prices = [(r.recorded_at, r.price) for r in records]
        backtest_trades = engine.simulate(strategy, prices)
        context["backtest"] = {
            "prices_count": len(prices),
            "trades": backtest_trades,
            "performance": engine.evaluate(backtest_trades, prices[-1][1] if prices else None),
            "buy_and_hold": engine.buy_and_hold_percent(prices),
            "chart": line_chart([p[0] for p in prices], [p[1] for p in prices], strategy.share.ticker)
            if prices else None,
        }
    return render(
        request,
        "investments/strategy_detail.html",
        context,
        status=400 if form.errors else 200,
    )


@login_required
@require_POST
def strategy_toggle(request, pk):
    strategy = get_object_or_404(Strategy, pk=pk, user=request.user)
    strategy.is_active = not strategy.is_active
    strategy.save(update_fields=["is_active"])
    return redirect("investments:strategy", pk=pk)


@login_required
@require_POST
def strategy_delete(request, pk):
    get_object_or_404(Strategy, pk=pk, user=request.user).delete()
    return redirect("investments:strategies")
