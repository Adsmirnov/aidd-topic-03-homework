from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dashboard.forms import InvestmentStrategyForm
from dashboard.models import InvestmentStrategy


@login_required(login_url="user:auth")
def strategies(request):
    strategy_list = (
        InvestmentStrategy.objects.filter(owner=request.user)
        .select_related("share")
        .prefetch_related("trades")
    )
    return render(
        request,
        "dashboard/strategies.html",
        {"strategies": strategy_list, "form": InvestmentStrategyForm()},
    )


@login_required(login_url="user:auth")
@require_POST
def create_strategy(request):
    form = InvestmentStrategyForm(request.POST)
    if form.is_valid():
        strategy = form.save(commit=False)
        strategy.owner = request.user
        strategy.save()
        messages.success(request, "Стратегия создана и запущена.")
    else:
        messages.error(request, form.errors.as_text())
    return redirect("dashboard:strategies:index")


@login_required(login_url="user:auth")
@require_POST
def toggle_strategy(request, strategy_id):
    strategy = get_object_or_404(InvestmentStrategy, pk=strategy_id, owner=request.user)
    strategy.is_active = not strategy.is_active
    strategy.save(update_fields=("is_active",))
    return redirect("dashboard:strategies:index")
