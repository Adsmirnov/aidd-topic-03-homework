from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard.forms import PriceAlertForm, WatchlistEntryForm, WatchlistForm
from dashboard.models import AlertNotification, PriceAlert, Watchlist, WatchlistEntry


@login_required(login_url="user:auth")
def monitoring(request):
    watchlists = (
        Watchlist.objects.filter(owner=request.user)
        .prefetch_related("entries__share", "entries__alerts")
        .order_by("name")
    )
    notifications = (
        AlertNotification.objects.filter(alert__entry__watchlist__owner=request.user)
        .select_related("alert__entry__share", "alert__entry__watchlist")
        .order_by("-created_at")[:50]
    )
    return render(
        request,
        "dashboard/monitoring.html",
        {
            "watchlists": watchlists,
            "notifications": notifications,
            "watchlist_form": WatchlistForm(owner=request.user),
            "entry_form": WatchlistEntryForm(),
            "alert_form": PriceAlertForm(),
        },
    )


@login_required(login_url="user:auth")
@require_POST
def create_watchlist(request):
    form = WatchlistForm(request.POST, owner=request.user)
    if form.is_valid():
        watchlist = form.save(commit=False)
        watchlist.owner = request.user
        watchlist.save()
        messages.success(request, "Список наблюдения создан.")
    else:
        messages.error(request, form.errors.as_text())
    return redirect("dashboard:monitoring:index")


@login_required(login_url="user:auth")
@require_POST
def add_watchlist_entry(request, watchlist_id):
    watchlist = get_object_or_404(Watchlist, pk=watchlist_id, owner=request.user)
    form = WatchlistEntryForm(request.POST)
    if form.is_valid():
        WatchlistEntry.objects.get_or_create(
            watchlist=watchlist,
            share=form.cleaned_data["share"],
        )
        messages.success(request, "Акция добавлена в список.")
    else:
        messages.error(request, form.errors.as_text())
    return redirect("dashboard:monitoring:index")


@login_required(login_url="user:auth")
@require_POST
def add_price_alert(request, entry_id):
    entry = get_object_or_404(
        WatchlistEntry,
        pk=entry_id,
        watchlist__owner=request.user,
    )
    form = PriceAlertForm(request.POST)
    if form.is_valid():
        PriceAlert.objects.get_or_create(
            entry=entry,
            direction=form.cleaned_data["direction"],
            target_price=form.cleaned_data["target_price"],
        )
        messages.success(request, "Ценовой уровень сохранён.")
    else:
        messages.error(request, form.errors.as_text())
    return redirect("dashboard:monitoring:index")


@login_required(login_url="user:auth")
@require_POST
def delete_watchlist_entry(request, entry_id):
    entry = get_object_or_404(
        WatchlistEntry,
        pk=entry_id,
        watchlist__owner=request.user,
    )
    entry.delete()
    return redirect("dashboard:monitoring:index")


@login_required(login_url="user:auth")
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        AlertNotification,
        pk=notification_id,
        alert__entry__watchlist__owner=request.user,
    )
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=("read_at",))
    return redirect("dashboard:monitoring")
