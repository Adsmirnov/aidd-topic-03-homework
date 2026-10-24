from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from investments.forms import AddShareForm, NameForm, PriceAlertForm
from investments.models import PriceAlert, Watchlist, WatchlistItem


@login_required
def watchlist_list(request):
    """Списки наблюдения пользователя и создание нового"""
    form = NameForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        watchlist = Watchlist.objects.create(user=request.user, name=form.cleaned_data["name"])
        return redirect("investments:watchlist", pk=watchlist.pk)
    watchlists = request.user.watchlists.prefetch_related("items__share")
    return render(
        request, "investments/watchlists.html", {"watchlists": watchlists, "form": form}
    )


@login_required
def watchlist_detail(request, pk):
    """Акции списка, их ценовые уровни и формы добавления"""
    watchlist = get_object_or_404(Watchlist, pk=pk, user=request.user)
    share_form = AddShareForm(request.POST or None, watchlist=watchlist)
    if request.method == "POST" and share_form.is_valid():
        WatchlistItem.objects.create(watchlist=watchlist, share=share_form.cleaned_data["ticker"])
        return redirect("investments:watchlist", pk=pk)
    items = watchlist.items.select_related("share").prefetch_related("alerts")
    return render(
        request,
        "investments/watchlist_detail.html",
        {
            "watchlist": watchlist,
            "items": items,
            "share_form": share_form,
            "rename_form": NameForm(initial={"name": watchlist.name}),
            "alert_form": PriceAlertForm(),
        },
    )


@login_required
@require_POST
def watchlist_rename(request, pk):
    watchlist = get_object_or_404(Watchlist, pk=pk, user=request.user)
    form = NameForm(request.POST)
    if form.is_valid():
        watchlist.name = form.cleaned_data["name"]
        watchlist.save()
    return redirect("investments:watchlist", pk=pk)


@login_required
@require_POST
def watchlist_delete(request, pk):
    get_object_or_404(Watchlist, pk=pk, user=request.user).delete()
    return redirect("investments:watchlists")


@login_required
@require_POST
def item_delete(request, pk):
    item = get_object_or_404(WatchlistItem, pk=pk, watchlist__user=request.user)
    item.delete()
    return redirect("investments:watchlist", pk=item.watchlist_id)


@login_required
@require_POST
def alert_create(request, item_pk):
    item = get_object_or_404(WatchlistItem, pk=item_pk, watchlist__user=request.user)
    form = PriceAlertForm(request.POST)
    if form.is_valid():
        form.instance.item = item
        form.save()
        return redirect("investments:watchlist", pk=item.watchlist_id)
    return render(
        request,
        "investments/alert_error.html",
        {"form": form, "item": item},
        status=400,
    )


@login_required
@require_POST
def alert_delete(request, pk):
    alert = get_object_or_404(PriceAlert, pk=pk, item__watchlist__user=request.user)
    alert.delete()
    return redirect("investments:watchlist", pk=alert.item.watchlist_id)


@login_required
@require_POST
def alert_rearm(request, pk):
    """Включить сработавший уровень снова: следующее выполнение условия — новое событие"""
    alert = get_object_or_404(PriceAlert, pk=pk, item__watchlist__user=request.user)
    alert.triggered_at = None
    alert.save(update_fields=["triggered_at"])
    return redirect("investments:watchlist", pk=alert.item.watchlist_id)


@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related("share")[:200]
    return render(request, "investments/notifications.html", {"notifications": notifications})


@login_required
@require_POST
def notifications_read(request):
    request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    return redirect("investments:notifications")
