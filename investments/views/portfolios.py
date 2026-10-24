from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from investments.forms import NameForm, OperationForm
from investments.models import Portfolio
from investments.services.portfolio import summarize


@login_required
def portfolio_list(request):
    """Портфели пользователя и создание нового"""
    form = NameForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        portfolio = Portfolio.objects.create(user=request.user, name=form.cleaned_data["name"])
        return redirect("investments:portfolio", pk=portfolio.pk)
    portfolios = [(p, summarize(p)) for p in request.user.portfolios.all()]
    return render(request, "investments/portfolios.html", {"portfolios": portfolios, "form": form})


@login_required
def portfolio_detail(request, pk):
    """Позиции, итоги, форма операции и история операций"""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    form = OperationForm(request.POST or None, portfolio=portfolio)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("investments:portfolio", pk=pk)
    operations = portfolio.operations.select_related("share").order_by("-executed_at", "-id")
    return render(
        request,
        "investments/portfolio_detail.html",
        {
            "portfolio": portfolio,
            "summary": summarize(portfolio),
            "operations": operations,
            "form": form,
        },
        status=400 if form.errors else 200,
    )


@login_required
@require_POST
def portfolio_rename(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    form = NameForm(request.POST)
    if form.is_valid():
        portfolio.name = form.cleaned_data["name"]
        portfolio.save()
    return redirect("investments:portfolio", pk=pk)


@login_required
@require_POST
def portfolio_delete(request, pk):
    get_object_or_404(Portfolio, pk=pk, user=request.user).delete()
    return redirect("investments:portfolios")
