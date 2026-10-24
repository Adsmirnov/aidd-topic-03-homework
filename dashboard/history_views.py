from datetime import datetime, time
from decimal import Decimal

from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import localdate
from datetime import timedelta
from plotly.graph_objs import Scatter
from plotly.offline import plot

from dashboard.forms import PriceHistoryFilterForm
from dashboard.models import PriceHistory


def price_history(request):
    initial = None
    if not request.GET:
        today = localdate()
        initial = {"start_date": today - timedelta(days=30), "end_date": today}
    form = PriceHistoryFilterForm(request.GET or None, initial=initial)
    entries = []
    plot_div = None
    absolute_change = None
    percent_change = None

    if form.is_valid() and form.cleaned_data.get("share"):
        queryset = PriceHistory.objects.filter(share=form.cleaned_data["share"])
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        if start_date:
            start_at = timezone.make_aware(
                datetime.combine(start_date, time.min), timezone.get_current_timezone()
            )
            queryset = queryset.filter(observed_at__gte=start_at)
        if end_date:
            end_at = timezone.make_aware(
                datetime.combine(end_date, time.max), timezone.get_current_timezone()
            )
            queryset = queryset.filter(observed_at__lte=end_at)

        entries = list(queryset.order_by("observed_at"))
        if entries:
            first_price = entries[0].price
            last_price = entries[-1].price
            absolute_change = last_price - first_price
            percent_change = (
                absolute_change / first_price * Decimal("100") if first_price else None
            )
            plot_div = plot(
                [
                    Scatter(
                        x=[entry.observed_at for entry in entries],
                        y=[float(entry.price) for entry in entries],
                        mode="lines+markers",
                        name=form.cleaned_data["share"].ticker,
                    )
                ],
                output_type="div",
            )

    return render(
        request,
        "dashboard/history.html",
        {
            "form": form,
            "entries": entries,
            "plot_div": plot_div,
            "absolute_change": absolute_change,
            "percent_change": percent_change,
        },
    )
